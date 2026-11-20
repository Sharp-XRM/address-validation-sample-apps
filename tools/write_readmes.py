"""Write <Provider>/README.md for every provider in providers.json.

Usage:
  python write_readmes.py
"""
import json
import os

from build_sample_apps import STANDARD, config_name, setup_page_name, solution_name
from flows import connection_reference_name, flow_name as flow_title

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def readme(cat, p):
    prefix = cat["publisher"]["prefix"]
    version = cat["version"].replace(".", "_")
    sol = solution_name(p)
    lines = [
        "# %s address autocomplete sample" % p["displayName"],
        "",
        "A ready-to-import model-driven app that shows the **%s** address autocomplete control of "
        "SharpXRM Address Validation for Dynamics 365 on Account and Contact forms, including their quick create forms." % p["displayName"],
        "",
        "## Install",
        "",
        "1. Make sure **Address Validation for D365** is installed and licensed in the environment (a trial licence works)%s." % (
            ", using %s" % p["requires"] if p.get("requires") else ""),
        "2. Download [`%s_%s_managed.zip`](../dist/%s_%s_managed.zip) and import it from **Power Apps > Solutions > Import solution**.%s" % (
            sol, version, sol, version,
            " When asked, pick (or create) a Microsoft Dataverse connection for the background verification flows." if p.get("verification") else ""),
        "3. Open the **%s Address Sample** app. It opens on the **Setup** page." % p["displayName"],
        "4. Enter your %s, then select **Save and validate**.%s" % (
            p["credential"]["label"],
            " Also enter the %s in step 2 for the background verification flows." % p["verification"]["credential"]["label"]
            if p.get("verification", {}).get("config") == "separate" else ""),
        "5. Select **New sample account** or **New sample contact**, type a street address in **Address search**, and pick a suggestion. "
        "**Quick create account** and **Quick create contact** open the same control on the quick create forms "
        "(also shown by **+ New** and the **Create** button in the app).",
    ]
    if p.get("tryIt"):
        lines.append("   For example: *%s*." % p["tryIt"])
    lines += [
        "",
        "## Getting a key",
        "",
        "Where to get it: %s" % p["credential"]["getKeyUrl"],
        "",
    ]
    lines += ["- %s" % h for h in p["credential"].get("hints", [])]
    lines += [
        "",
        "## What the forms show",
        "",
        "| Control output | Column on Account and Contact |",
        "|---|---|",
    ]
    for o in p["outputs"]:
        if "std" in o:
            lines.append("| `%s` | %s (`%s`, standard) |" % (o["prop"], STANDARD[o["std"]][0], o["std"]))
        else:
            lines.append("| `%s` | %s (`%s_%s_%s`, sample column) |" % (o["prop"], o["label"], prefix, p["code"], o["column"]))
    inputs = p.get("inputs") or {}
    v = p.get("verification")
    if v:
        lines.append("| *(flows)* | Last Verified Address (`%s_%s_verifiedaddress`, sample column used by the flows) |" % (prefix, p["code"]))
        if v.get("config") == "separate":
            key_text = ("The flows need a **%s**, entered in step 2 of the Setup page. It is stored in the API Configuration "
                        "record **SharpXrmSample_%s_Verify**." % (v["credential"]["label"], p["key"]))
        elif v.get("config") == "sameKey":
            key_text = ("The flows use the same Melissa licence key with **Melissa Global Address Verification**. When you save the key, "
                        "the Setup page also creates the API Configuration **SharpXrmSample_%s_Verify** and the Field Mappings "
                        "**SharpXrmSample_%s_account** and **SharpXrmSample_%s_contact** that the flows use." % (p["key"], p["key"], p["key"]))
        else:
            key_text = "The flows use the same key as the autocomplete control."
        lines += [
            "",
            "## Background verification (Power Automate)",
            "",
            "The solution includes two cloud flows, **%s** and **%s**. Each one:" % (
                flow_title(p, "account"), flow_title(p, "contact")),
            "",
            "1. Runs when the address of an Account (or Contact) is added or changed.",
            "2. Checks the address with %s (`%s`%s) through the Microsoft Dataverse connector." % (
                v["label"], v["api"], " or `%s` outside %s" % (v["internationalApi"], "the US and Canada" if "canada" in v.get("domesticCountries", []) else "the US") if v.get("internationalApi") else ""),
            "3. Writes the verified address back to the standard address columns (street, unit, city, county, state, ZIP or postal code, country, latitude and longitude).",
            "4. Adds a note to the record with every value the action returned, the address it sent, what it wrote back, and the full raw response. The notes appear in the **Notes** section of the sample forms.",
            "",
            key_text,
            "",
            "To keep them safe in a real environment, the flows only act on records whose address was picked with this sample's control "
            "(the *Full Address* sample column is filled). They never touch your other Accounts and Contacts, and several samples can be installed side by side. "
            "They also skip their own updates, using the *Last Verified Address* column (it reads `PENDING` while a check is running).",
            "",
            "When you import the solution, Power Apps asks for a Microsoft Dataverse connection for the connection reference "
            "**%s sample - Dataverse**. Pick or create one and the flows are turned on. Each address change costs one verification call with %s." % (
                p["displayName"], p["displayName"]),
        ]
    lines += [
        "",
        "## What the solution contains",
        "",
        "| Component | Name |",
        "|---|---|",
        "| Solution | `%s` (publisher *%s*, prefix `%s`) |" % (sol, cat["publisher"]["friendlyname"], prefix),
        "| App | %s Address Sample (`%s_%sSample`) |" % (p["displayName"], prefix, p["key"]),
        "| Forms | Account - %s Sample, Contact - %s Sample |" % (p["displayName"], p["displayName"]),
        "| Quick create forms | Account Quick Create - %s Sample, Contact Quick Create - %s Sample |" % (p["displayName"], p["displayName"]),
        "| Setup page | `%s` |" % setup_page_name(prefix, p),
        "| Columns | `%s_%s_*` on Account and Contact |" % (prefix, p["code"]),
        "| Control | `%s` (from Address Validation for D365) |" % p["control"],
        "",
        "The Setup page stores your key in the API Configuration record named **%s**, which the sample forms use. "
        "Removing the solution does not delete that record." % config_name(p),
    ]
    if v:
        at = next(i for i, l in enumerate(lines) if l.startswith("| Control |")) + 1
        lines[at:at] = [
            "| Flows | %s, %s |" % (flow_title(p, "account"), flow_title(p, "contact")),
            "| Connection reference | `%s` (Microsoft Dataverse) |" % connection_reference_name(prefix, p),
        ]
    if inputs:
        lines += [
            "",
            "The control on the sample forms uses these settings, which you can change in the form designer: %s." %
            ", ".join("`%s` = `%s`" % (k, v) for k, v in inputs.items()),
        ]
    lines += [
        "",
        "## Source",
        "",
        "[`src`](src) holds the unpacked solution (both managed and unmanaged). Rebuild the zips with "
        "`pac solution pack --zipfile %s.zip --folder src --packagetype Both`." % sol,
        "",
    ]
    return "\n".join(lines)


def main():
    with open(os.path.join(HERE, "providers.json"), encoding="utf-8") as f:
        cat = json.load(f)
    for p in cat["providers"]:
        folder = os.path.join(ROOT, p["key"])
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "README.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(readme(cat, p))
        print("wrote %s/README.md" % p["key"])


if __name__ == "__main__":
    main()
