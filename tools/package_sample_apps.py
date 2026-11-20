"""Finish, export and unpack the SharpXRM sample app solutions built by build_sample_apps.py.

For every provider in providers.json:
  1. Makes sure the app lists the Account and Contact tables. The Web API cannot add tables to an
     app (AddAppComponents stores the 'entity' table instead), so the solution is exported, the
     tables are written into AppModule.xml, and the solution is imported back.
  2. Exports the unmanaged and managed solutions to dist/.
  3. Unpacks both into <Provider>/src so the source can be reviewed and rebuilt with
     `pac solution pack`.

Prerequisites: the Power Platform CLI (pac) with an auth profile for the environment, the Azure CLI
signed in (`az login`), and Python 3.9+.

Usage:
  python package_sample_apps.py --env https://yourorg.crm.dynamics.com [--only GoogleMaps,Smarty]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from build_sample_apps import Dataverse, app_unique_name, solution_name

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TABLES = ("account", "contact")


def pac(*args):
    exe = shutil.which("pac") or shutil.which("pac.cmd")
    if not exe:
        sys.exit("The Power Platform CLI (pac) was not found.")
    result = subprocess.run([exe] + list(args), capture_output=True, text=True)
    if result.returncode != 0 or "Error:" in result.stdout:
        sys.exit("pac %s failed:\n%s\n%s" % (" ".join(args), result.stdout, result.stderr))
    return result.stdout


def remove_entity_search_rows(dv, prefix):
    """Dataverse search rows created for the bogus 'entity' app component."""
    searches = dv.call("GET", "dvtablesearchs?$select=dvtablesearchid,name&$filter=contains(name,'model_%s_')" % prefix).get("value", [])
    ids = {s["dvtablesearchid"] for s in searches}
    rows = dv.call("GET", "dvtablesearchentities?$select=dvtablesearchentityid,_dvtablesearch_value&$filter=entitylogicalname eq 'entity'").get("value", [])
    for row in rows:
        if row["_dvtablesearch_value"] in ids:
            dv.call("DELETE", "dvtablesearchentities(%s)" % row["dvtablesearchentityid"])
            print("  removed search row for the 'entity' table")


def patch_app_tables(app_xml_path):
    with open(app_xml_path, encoding="utf-8") as f:
        xml = f.read()
    wanted = "".join('<AppModuleComponent type="1" schemaName="%s" />' % t for t in TABLES)
    current = "".join(re.findall(r'<AppModuleComponent type="1"[^>]*/>', xml))
    if current.replace(" ", "") == wanted.replace(" ", ""):
        return False
    xml = re.sub(r'\s*<AppModuleComponent type="1"[^>]*/>', "", xml)
    xml = xml.replace("<AppModuleComponents>", "<AppModuleComponents>" + wanted, 1)
    with open(app_xml_path, "w", encoding="utf-8", newline="") as f:
        f.write(xml)
    return True


def ensure_app_tables(env, p, prefix, work):
    name = solution_name(p)
    zip_path = os.path.join(work, name + ".zip")
    src = os.path.join(work, "src")
    pac("solution", "export", "--name", name, "--path", zip_path, "--environment", env, "--overwrite")
    pac("solution", "unpack", "--zipfile", zip_path, "--folder", src, "--packagetype", "Unmanaged", "--allowDelete", "true")
    app_xml = os.path.join(src, "AppModules", app_unique_name(prefix, p), "AppModule.xml")
    if not patch_app_tables(app_xml):
        return
    print("  adding Account and Contact to the app through a solution import")
    fixed = os.path.join(work, name + "_fixed.zip")
    pac("solution", "pack", "--zipfile", fixed, "--folder", src, "--packagetype", "Unmanaged")
    pac("solution", "import", "--path", fixed, "--environment", env, "--publish-changes")


def export(env, p, version):
    name = solution_name(p)
    dist = os.path.join(ROOT, "dist")
    os.makedirs(dist, exist_ok=True)
    stem = "%s_%s" % (name, version.replace(".", "_"))
    unmanaged = os.path.join(dist, stem + ".zip")
    managed = os.path.join(dist, stem + "_managed.zip")
    pac("solution", "export", "--name", name, "--path", unmanaged, "--environment", env, "--overwrite")
    pac("solution", "export", "--name", name, "--path", managed, "--managed", "--environment", env, "--overwrite")

    # pac unpacks both package types from <name>.zip and <name>_managed.zip side by side.
    with tempfile.TemporaryDirectory() as work:
        shutil.copy(unmanaged, os.path.join(work, name + ".zip"))
        shutil.copy(managed, os.path.join(work, name + "_managed.zip"))
        src = os.path.join(ROOT, p["key"], "src")
        if os.path.isdir(src):
            shutil.rmtree(src)
        pac("solution", "unpack", "--zipfile", os.path.join(work, name + ".zip"), "--folder", src, "--packagetype", "Both")
    print("  exported %s and %s" % (os.path.basename(unmanaged), os.path.basename(managed)))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", required=True)
    parser.add_argument("--only")
    args = parser.parse_args()
    env = args.env.rstrip("/") + "/"

    with open(os.path.join(HERE, "providers.json"), encoding="utf-8") as f:
        catalogue = json.load(f)
    providers = catalogue["providers"]
    if args.only:
        wanted = {k.strip().lower() for k in args.only.split(",")}
        providers = [p for p in providers if p["key"].lower() in wanted]

    dv = Dataverse(args.env)
    prefix = catalogue["publisher"]["prefix"]
    for p in providers:
        print("== %s" % p["displayName"])
        with tempfile.TemporaryDirectory() as work:
            ensure_app_tables(env, p, prefix, work)
        remove_entity_search_rows(dv, prefix)
        export(env, p, catalogue["version"])


if __name__ == "__main__":
    main()
