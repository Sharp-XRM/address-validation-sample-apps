"""Build or refresh the SharpXRM address autocomplete sample apps in a Dataverse environment.

For every provider in providers.json the tool creates (or updates) one unmanaged solution with:
  * custom columns on Account and Contact for the control outputs that have no standard column
  * an Account form and a Contact form wired to the provider's autocomplete control
  * an Account and a Contact quick create form with the same control
  * a Setup page (HTML web resource) to enter the provider's API key
  * a model-driven app (app module + site map) that ties them together

The tool is idempotent: components get stable ids, so running it again updates them in place.

Prerequisites: Python 3.9+, the Azure CLI signed in (`az login`) with access to the environment,
and the Address Validation for D365 solution installed in it.

Usage:
  python build_sample_apps.py --env https://yourorg.crm.dynamics.com [--only GoogleMaps,Smarty]
"""
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from xml.sax.saxutils import escape, quoteattr

import flows

HERE = os.path.dirname(os.path.abspath(__file__))
ID_NAMESPACE = uuid.UUID("6f2b8e1c-4a5d-4f3e-9b7a-5c1d2e3f4a5b")

CLASS_TEXT = "{4273EDBD-AC1D-40d3-9FB2-095C621B552D}"
CLASS_MEMO = "{E0DECE4B-6FC8-4a8f-A065-082708572369}"
CLASS_FLOAT = "{0D2C745A-E5A8-4c8f-BA63-C6D3BB604660}"
CLASS_LOOKUP = "{270BD3DB-D9AF-4782-9025-509E298DEC0A}"
CLASS_EMAIL = "{ADA2203E-B4CD-49be-9DDF-234642B43B52}"
CLASS_URL = "{71716B6C-711E-476c-8AB8-5D11542BFB47}"
CLASS_PHONE = "{8C10015A-B339-4982-9474-A95FE05631A5}"
CLASS_PCF_HOST = "{F9A8A302-114E-466A-B582-6771B2AE0D92}"
CLASS_TIMELINE = "{06375649-c143-495e-a496-c962e5b4488e}"
DEFAULT_APP_ICON = "953b9fac-1e5e-e611-80d6-00155ded156f"

# Standard columns used on the sample forms: logical name -> (label, form control class).
STANDARD = {
    "name": ("Account Name", CLASS_TEXT),
    "firstname": ("First Name", CLASS_TEXT),
    "lastname": ("Last Name", CLASS_TEXT),
    "jobtitle": ("Job Title", CLASS_TEXT),
    "telephone1": ("Phone", CLASS_PHONE),
    "mobilephone": ("Mobile Phone", CLASS_PHONE),
    "emailaddress1": ("Email", CLASS_EMAIL),
    "websiteurl": ("Website", CLASS_URL),
    "primarycontactid": ("Primary Contact", CLASS_LOOKUP),
    "parentcustomerid": ("Company Name", CLASS_LOOKUP),
    "address1_line1": ("Street 1", CLASS_TEXT),
    "address1_line2": ("Street 2", CLASS_TEXT),
    "address1_city": ("City", CLASS_TEXT),
    "address1_county": ("County", CLASS_TEXT),
    "address1_stateorprovince": ("State/Province", CLASS_TEXT),
    "address1_postalcode": ("ZIP/Postal Code", CLASS_TEXT),
    "address1_country": ("Country/Region", CLASS_TEXT),
    "address1_latitude": ("Latitude", CLASS_FLOAT),
    "address1_longitude": ("Longitude", CLASS_FLOAT),
}
CUSTOM_CLASS = {"text": CLASS_TEXT, "phone": CLASS_PHONE, "url": CLASS_URL, "memo": CLASS_MEMO}
# Control input types other than SingleLine.Text.
INPUT_TYPES = {
    "displayAddressFields": "Enum", "searchScope": "Enum", "nativeCharset": "Enum", "diacritics": "Enum",
    "subdivisionCodeFormat": "Enum", "maxResults": "Whole.None", "cacheTtlHours": "Whole.None",
}
# Order in which the standard address columns appear on the form.
STANDARD_ADDRESS_ORDER = [
    "address1_line1", "address1_line2", "address1_city", "address1_county", "address1_stateorprovince",
    "address1_postalcode", "address1_country", "address1_latitude", "address1_longitude",
]


def stable_id(*parts):
    return str(uuid.uuid5(ID_NAMESPACE, "/".join(parts)))


def label(text):
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel", "Label": text, "LanguageCode": 1033}],
    }


class Dataverse:
    def __init__(self, url):
        self.url = url.rstrip("/")
        self.api = self.url + "/api/data/v9.2/"
        self.token = self._token()

    def _token(self):
        az = shutil.which("az") or shutil.which("az.cmd")
        if not az:
            sys.exit("The Azure CLI (az) was not found. Install it and run `az login`.")
        result = subprocess.run([az, "account", "get-access-token", "--resource", self.url, "--query", "accessToken", "-o", "tsv"],
                                capture_output=True, text=True)
        if result.returncode != 0:
            sys.exit("Could not get a token for %s. Run `az login` first.\n%s" % (self.url, result.stderr))
        return result.stdout.strip()

    def call(self, method, path, body=None, solution=None, prefer=None, ok404=False):
        headers = {
            "Authorization": "Bearer " + self.token,
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
            data = json.dumps(body).encode("utf-8")
        if solution:
            headers["MSCRM.SolutionUniqueName"] = solution
        if prefer:
            headers["Prefer"] = prefer
        request = urllib.request.Request(self.api + urllib.parse.quote(path, safe="/?&=$(),'@.:-_*"), data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                text = response.read().decode("utf-8")
                if text:
                    return json.loads(text)
                entity_id = response.headers.get("OData-EntityId") or ""
                return {"@id": entity_id[entity_id.rfind("(") + 1:-1]} if "(" in entity_id else {}
        except urllib.error.HTTPError as error:
            text = error.read().decode("utf-8", "replace")
            if ok404 and error.code == 404:
                return None
            try:
                message = json.loads(text)["error"]["message"]
            except Exception:
                message = text
            raise RuntimeError("%s %s failed (%s): %s" % (method, path.split("?")[0], error.code, message))

    def first(self, path):
        result = self.call("GET", path)
        values = result.get("value", [])
        return values[0] if values else None


class Builder:
    def __init__(self, dv, catalogue):
        self.dv = dv
        self.cat = catalogue
        self.pub = catalogue["publisher"]
        self.prefix = self.pub["prefix"]
        self.connection_id = None

    # ------------------------------------------------------------------ publisher / solution

    def ensure_publisher(self):
        pub = self.dv.first("publishers?$select=publisherid&$filter=uniquename eq '%s'" % self.pub["uniquename"])
        if pub:
            return pub["publisherid"]
        print("  creating publisher %s" % self.pub["uniquename"])
        self.dv.call("POST", "publishers", {
            "uniquename": self.pub["uniquename"],
            "friendlyname": self.pub["friendlyname"],
            "customizationprefix": self.prefix,
            "customizationoptionvalueprefix": self.pub["optionvalueprefix"],
            "description": self.pub["description"],
            "supportingwebsiteurl": self.pub["website"],
        })
        return self.dv.first("publishers?$select=publisherid&$filter=uniquename eq '%s'" % self.pub["uniquename"])["publisherid"]

    def ensure_solution(self, p, publisher_id):
        name = solution_name(p)
        body = {
            "friendlyname": "SharpXRM Sample - %s" % p["displayName"],
            "version": self.cat["version"],
            "description": "Sample app for the %s address autocomplete control of SharpXRM Address Validation for Dynamics 365. "
                           "Requires the Address Validation for D365 solution." % p["displayName"],
        }
        sol = self.dv.first("solutions?$select=solutionid&$filter=uniquename eq '%s'" % name)
        if sol:
            self.dv.call("PATCH", "solutions(%s)" % sol["solutionid"], body)
            return name
        print("  creating solution %s" % name)
        body.update({"uniquename": name, "publisherid@odata.bind": "/publishers(%s)" % publisher_id})
        self.dv.call("POST", "solutions", body)
        return name

    def add_to_solution(self, solution, component_id, component_type):
        self.dv.call("POST", "AddSolutionComponent", {
            "ComponentId": component_id,
            "ComponentType": component_type,
            "SolutionUniqueName": solution,
            "AddRequiredComponents": False,
            "DoNotIncludeSubcomponents": False,
        })

    # ------------------------------------------------------------------ columns

    def column_name(self, p, output):
        return "%s_%s_%s" % (self.prefix, p["code"], output["column"])

    def ensure_column(self, table, p, output, solution):
        logical = self.column_name(p, output)
        path = "EntityDefinitions(LogicalName='%s')/Attributes(LogicalName='%s')?$select=MetadataId" % (table, logical)
        existing = self.dv.call("GET", path, ok404=True)
        if existing:
            self.add_to_solution(solution, existing["MetadataId"], 2)
            return logical
        display = "%s (%s)" % (output["label"], p["displayName"])
        description = output.get("description") or "Output '%s' of the %s address autocomplete control (sample app)." % (
            output["prop"], p["displayName"])
        common = {
            "SchemaName": logical,
            "DisplayName": label(display),
            "Description": label(description),
            "RequiredLevel": {"Value": "None", "CanBeChanged": True, "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings"},
        }
        if output["type"] == "memo":
            body = dict(common, **{
                "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
                "AttributeType": "Memo",
                "AttributeTypeName": {"Value": "MemoType"},
                "Format": "TextArea",
                "MaxLength": output["max"],
            })
        else:
            body = dict(common, **{
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "AttributeType": "String",
                "AttributeTypeName": {"Value": "StringType"},
                "FormatName": {"Value": {"text": "Text", "phone": "Phone", "url": "Url"}[output["type"]]},
                "MaxLength": output["max"],
            })
        print("  creating column %s.%s" % (table, logical))
        self.dv.call("POST", "EntityDefinitions(LogicalName='%s')/Attributes" % table, body, solution=solution)
        return logical

    # ------------------------------------------------------------------ forms

    @staticmethod
    def layout(*scope):
        """Returns cell() and section() builders whose ids are stable within the given scope (provider, table, form)."""

        def cell(field, text, classid, control_id=None, uniqueid=None, showlabel=True, disabled=False):
            cid = stable_id(*scope, "cell", control_id or field)
            attrs = 'id=%s classid=%s datafieldname=%s disabled="%s"' % (
                quoteattr(control_id or field), quoteattr(classid), quoteattr(field), "true" if disabled else "false")
            if uniqueid:
                attrs += " uniqueid=%s" % quoteattr("{%s}" % uniqueid)
            return ('<row><cell id="{%s}" showlabel="%s"><labels><label description=%s languagecode="1033" /></labels>'
                    '<control %s /></cell></row>') % (cid, "true" if showlabel else "false", quoteattr(text), attrs)

        def section(name, text, rows):
            sid = stable_id(*scope, "section", name)
            return ('<section name=%s showlabel="true" showbar="false" id="{%s}" IsUserDefined="1" layout="varwidth" columns="1" '
                    'labelwidth="140" celllabelposition="Left"><labels><label description=%s languagecode="1033" /></labels>'
                    '<rows>%s</rows></section>') % (quoteattr(name), sid, quoteattr(text), "".join(rows))

        return cell, section

    def address_rows(self, cell, p, table, host_id):
        """Rows shared by the main and quick create forms: the search control host, standard address columns, extra outputs."""
        details = [cell(f, STANDARD[f][0], STANDARD[f][1]) for f in self.cat["tables"][table]["details"]]
        search = [cell("address1_line1", "Address search", CLASS_PCF_HOST, uniqueid=host_id, showlabel=False)]
        std_fields = {o["std"] for o in p["outputs"] if "std" in o}
        standard_rows = []
        for f in STANDARD_ADDRESS_ORDER:
            if f in std_fields:
                control_id = "address1_line11" if f == "address1_line1" else None
                standard_rows.append(cell(f, STANDARD[f][0], STANDARD[f][1], control_id=control_id))
        custom_rows = [cell(self.column_name(p, o), o["label"], CUSTOM_CLASS[o["type"]]) for o in p["outputs"] if "column" in o]
        return details, search, standard_rows, custom_rows

    def control_descriptions(self, p, host_id):
        """Binds the provider's autocomplete control to the host cell for web, tablet and phone."""
        params = ['<apiConfigName type="SingleLine.Text" static="true">%s</apiConfigName>' % escape(config_name(p))]
        for o in p["outputs"]:
            target = o["std"] if "std" in o else self.column_name(p, o)
            params.append("<%s>%s</%s>" % (o["prop"], target, o["prop"]))
        for name, value in p.get("inputs", {}).items():
            params.append('<%s type="%s" static="true">%s</%s>' % (name, INPUT_TYPES.get(name, "SingleLine.Text"), escape(value), name))
        pcf = "".join('<customControl name="%s" formFactor="%d"><parameters>%s</parameters></customControl>' % (
            p["control"], factor, "".join(params)) for factor in (0, 1, 2))
        return ('<controlDescriptions><controlDescription forControl="{%s}">'
                '<customControl id="%s"><parameters><datafieldname>address1_line1</datafieldname></parameters></customControl>'
                '%s</controlDescription></controlDescriptions>') % (host_id, CLASS_TEXT, pcf)

    def form_xml(self, table, p):
        key = p["key"]
        cell, section = self.layout(key, table)
        host_id = stable_id(key, table, "pcf-host")
        details, search, standard_rows, custom_rows = self.address_rows(cell, p, table, host_id)

        tab_id = stable_id(key, table, "tab")
        left = section("sample_details", "Details", details) + section("sample_search", "Address search", search)
        if p.get("verification"):
            fp_cell = cell(flows.fingerprint_column(self.prefix, p), "Last verified address", CLASS_TEXT, disabled=True)
            timeline = ('<row><cell id="{%s}" showlabel="false" rowspan="20" auto="false" colspan="1"><labels><label description="Notes" '
                        'languagecode="1033" /></labels><control id="notescontrol" classid="%s" disabled="false" /></cell></row>%s') % (
                stable_id(key, table, "cell", "notescontrol"), CLASS_TIMELINE, "<row />" * 19)
            left += section("sample_notes", "Notes (results of the %s verification flow)" % p["displayName"], [fp_cell, timeline])
        right = (section("sample_standard", "Validated address (standard columns)", standard_rows) +
                 section("sample_outputs", "Extra %s outputs (sample columns)" % p["displayName"], custom_rows))
        tab = ('<tab name="sample_tab" id="{%s}" IsUserDefined="1" showlabel="true" expanded="true" verticallayout="true">'
               '<labels><label description="%s address sample" languagecode="1033" /></labels><columns>'
               '<column width="50%%"><sections>%s</sections></column>'
               '<column width="50%%"><sections>%s</sections></column></columns></tab>') % (
            tab_id, escape(p["displayName"]), left, right)

        header = ('<header id="{%s}" columns="111" celllabelposition="Top" labelwidth="115"><rows><row>'
                  '<cell id="{%s}" showlabel="true"><labels><label description="Owner" languagecode="1033" /></labels>'
                  '<control id="header_ownerid" classid="%s" datafieldname="ownerid" /></cell></row></rows></header>') % (
            stable_id(key, table, "header"), stable_id(key, table, "header-owner"), CLASS_LOOKUP)

        return '<form showImage="true" headerdensity="HighWithControls"><tabs>%s</tabs>%s%s</form>' % (
            tab, header, self.control_descriptions(p, host_id))

    def quick_create_xml(self, table, p):
        # Quick create forms have one tab with three columns, no header, and no Notes or other subgrids.
        key = p["key"]
        cell, section = self.layout(key, table, "quickcreate")
        host_id = stable_id(key, table, "quickcreate", "pcf-host")
        details, search, standard_rows, custom_rows = self.address_rows(cell, p, table, host_id)
        columns = [
            section("qc_details", "Details", details) + section("qc_search", "Address search", search),
            section("qc_standard", "Validated address (standard columns)", standard_rows),
            section("qc_outputs", "Extra %s outputs (sample columns)" % p["displayName"], custom_rows),
        ]
        tab = ('<tab name="qc_tab" id="{%s}" IsUserDefined="0" showlabel="false" expanded="true">'
               '<labels><label description="Quick create" languagecode="1033" /></labels><columns>%s</columns></tab>') % (
            stable_id(key, table, "quickcreate", "tab"),
            "".join('<column width="33%%"><sections>%s</sections></column>' % c for c in columns))
        return '<form><tabs>%s</tabs>%s</form>' % (tab, self.control_descriptions(p, host_id))

    def ensure_form(self, table, p, solution, quick_create=False):
        table_name = self.cat["tables"][table]["displayName"]
        if quick_create:
            form_id = stable_id(p["key"], table, "quickcreate-form")
            name = "%s Quick Create - %s Sample" % (table_name, p["displayName"])
            description = ("Sample quick create form for the %s address autocomplete control (shown by + New and the "
                           "Create button in the sample app)." % p["displayName"])
            formxml, form_type = self.quick_create_xml(table, p), 7
        else:
            form_id = stable_id(p["key"], table, "form")
            name = "%s - %s Sample" % (table_name, p["displayName"])
            description = ("Sample form for the %s address autocomplete control. Shows the standard address columns and "
                           "every extra output of the control." % p["displayName"])
            formxml, form_type = self.form_xml(table, p), 2
        body = {"name": name, "description": description, "formxml": formxml}
        existing = self.dv.call("GET", "systemforms(%s)?$select=formid" % form_id, ok404=True)
        if existing:
            self.dv.call("PATCH", "systemforms(%s)" % form_id, body)
        else:
            print("  creating form %s" % name)
            body.update({"formid": form_id, "objecttypecode": table, "type": form_type, "formactivationstate": 1})
            for attempt in range(6):
                try:
                    self.dv.call("POST", "systemforms", body, solution=solution)
                    break
                except RuntimeError as error:
                    # New columns can take a few seconds to reach the metadata cache used to validate forms.
                    if "non-existent attribute" not in str(error) or attempt == 5:
                        raise
                    time.sleep(15)
        self.add_to_solution(solution, form_id, 60)
        return form_id

    # ------------------------------------------------------------------ setup page

    def ensure_setup_page(self, p, forms, quick_forms, solution, flows_ids=None):
        with open(os.path.join(HERE, "setup-page", "setup.html"), encoding="utf-8") as f:
            template = f.read()
        settings = {
            "providerName": p["displayName"],
            "serviceType": p["serviceType"],
            "licenceName": p["licenceName"],
            "configName": config_name(p),
            "solutionName": solution,
            "credential": p["credential"],
            "tryIt": p.get("tryIt", ""),
            "forms": forms,
            "quickCreateForms": quick_forms,
        }
        v = p.get("verification")
        if v:
            settings["verification"] = {
                "label": v["label"],
                "config": v["config"],
                "mode": v.get("mode", "customApi"),
                "configName": flows.verify_config_name(p),
                "serviceType": v.get("serviceType", p["serviceType"]),
                "credential": v.get("credential"),
                "keyNote": v.get("keyNote", ""),
                "flows": [{"table": t, "id": flows_ids[t], "name": flows.flow_name(p, t)} for t in ("account", "contact")],
                "fieldMappings": {t: flows.field_mapping_name(p, t) for t in ("account", "contact")},
                "fingerprintColumn": flows.fingerprint_column(self.prefix, p),
                "melissaFullAddressColumn": "%s_%s_fulladdress" % (self.prefix, p["code"]),
            }
        html = template.replace("/*__SAMPLE_CONFIG__*/null", json.dumps(settings, indent=2).replace("</", "<\\/"))
        name = setup_page_name(self.prefix, p)
        body = {
            "displayname": "%s sample - Setup" % p["displayName"],
            "description": "Enter the %s API key for the sample app." % p["displayName"],
            "content": base64.b64encode(html.encode("utf-8")).decode("ascii"),
        }
        wr_id = stable_id(p["key"], "setup-page")
        existing = self.dv.call("GET", "webresourceset(%s)?$select=webresourceid" % wr_id, ok404=True)
        if existing:
            self.dv.call("PATCH", "webresourceset(%s)" % wr_id, body)
        else:
            print("  creating web resource %s" % name)
            body.update({"webresourceid": wr_id, "name": name, "webresourcetype": 1})
            self.dv.call("POST", "webresourceset", body, solution=solution)
        self.add_to_solution(solution, wr_id, 61)
        return wr_id

    # ------------------------------------------------------------------ app

    def sitemap_xml(self, p):
        page = setup_page_name(self.prefix, p)
        return (
            '<SiteMap IntroducedVersion="7.0.0.0">'
            '<Area Id="sxs_area" ResourceId="SitemapDesigner.NewArea" ShowGroups="true" IntroducedVersion="7.0.0.0">'
            '<Titles><Title LCID="1033" Title="%(name)s sample" /></Titles>'
            '<Group Id="sxs_group_start" ResourceId="SitemapDesigner.NewGroup" IsProfile="false" IntroducedVersion="7.0.0.0">'
            '<Titles><Title LCID="1033" Title="Get started" /></Titles>'
            '<SubArea Id="sxs_setup" Url="$webresource:%(page)s" AvailableOffline="false" PassParams="false" '
            'Client="All,Outlook,OutlookLaptopClient,OutlookWorkstationClient,Web" IntroducedVersion="7.0.0.0">'
            '<Titles><Title LCID="1033" Title="Setup" /></Titles></SubArea>'
            '</Group>'
            '<Group Id="sxs_group_records" ResourceId="SitemapDesigner.NewGroup" IsProfile="false" IntroducedVersion="7.0.0.0">'
            '<Titles><Title LCID="1033" Title="Sample records" /></Titles>'
            '<SubArea Id="sxs_accounts" Entity="account" AvailableOffline="true" PassParams="false" '
            'Client="All,Outlook,OutlookLaptopClient,OutlookWorkstationClient,Web" IntroducedVersion="7.0.0.0" />'
            '<SubArea Id="sxs_contacts" Entity="contact" AvailableOffline="true" PassParams="false" '
            'Client="All,Outlook,OutlookLaptopClient,OutlookWorkstationClient,Web" IntroducedVersion="7.0.0.0" />'
            '</Group></Area></SiteMap>'
        ) % {"name": escape(p["displayName"]), "page": page}

    def ensure_app(self, p, form_ids, solution):
        unique = app_unique_name(self.prefix, p)
        display = "%s Address Sample" % p["displayName"]

        sitemap_body = {"sitemapname": display, "sitemapxml": self.sitemap_xml(p), "isappaware": True}
        sitemap = self.find("sitemaps", "sitemapid", "sitemapnameunique eq '%s'" % unique)
        if sitemap:
            sitemap_id = sitemap["sitemapid"]
            if sitemap.get("_published"):
                self.dv.call("PATCH", "sitemaps(%s)" % sitemap_id, sitemap_body)
        else:
            print("  creating site map %s" % unique)
            sitemap_body["sitemapnameunique"] = unique
            sitemap_id = self.dv.call("POST", "sitemaps", sitemap_body, solution=solution)["@id"]
        self.add_to_solution(solution, sitemap_id, 62)

        app_body = {
            "name": display,
            "description": "Try the %s address autocomplete control on sample Account and Contact forms. "
                           "Start with Setup to enter your API key." % p["displayName"],
            "webresourceid": DEFAULT_APP_ICON,
        }
        app = self.find("appmodules", "appmoduleid,appmoduleidunique", "uniquename eq '%s'" % unique)
        if app:
            if app.get("_published"):
                self.dv.call("PATCH", "appmodules(%s)" % app["appmoduleid"], app_body)
        else:
            print("  creating app %s" % unique)
            app_body.update({"uniquename": unique, "clienttype": 4, "navigationtype": 0, "formfactor": 1})
            self.dv.call("POST", "appmodules", app_body, solution=solution)
            app = self.find("appmodules", "appmoduleid,appmoduleidunique", "uniquename eq '%s'" % unique)
        app_id = app["appmoduleid"]
        self.add_to_solution(solution, app_id, 80)

        # Tables are not added here: AddAppComponents drops the id of entity components and stores the
        # 'entity' table instead. package_sample_apps.py writes account and contact into AppModule.xml.
        components = [{"@odata.type": "Microsoft.Dynamics.CRM.sitemap", "sitemapid": sitemap_id}]
        for form_id in form_ids:
            components.append({"@odata.type": "Microsoft.Dynamics.CRM.systemform", "formid": form_id})
        existing = self.app_component_ids(app["appmoduleidunique"])
        missing = [c for c in components if self.component_key(c) not in existing]
        if missing:
            self.dv.call("POST", "AddAppComponents", {"AppId": app_id, "Components": missing})

        validation = self.dv.call("GET", "ValidateApp(AppModuleId=%s)" % app_id)
        issues = (validation.get("AppValidationResponse") or {}).get("ValidationIssueList") or []
        tables_pending = False
        for issue in issues:
            needs = [c.get("SchemaName") for c in issue.get("RequiredComponents") or []]
            if (needs and set(needs) <= {"account", "contact"}) or "at least one entity" in (issue.get("Message") or ""):
                tables_pending = True
            elif issue.get("Message"):
                print("  app validation %s: %s" % (issue.get("ErrorType"), issue["Message"]))
            elif needs:
                print("  app validation %s: %s needs %s" % (issue.get("ErrorType"), issue.get("DisplayName"), ", ".join(needs)))
        if tables_pending:
            print("  note: run package_sample_apps.py to add the Account and Contact tables to the app")
        return app_id, sitemap_id

    @staticmethod
    def component_key(component):
        return next(v for k, v in component.items() if not k.startswith("@")).lower()

    def app_component_ids(self, app_unique_id):
        result = self.dv.call("GET", "appmodulecomponents?$select=objectid&$filter=_appmoduleidunique_value eq %s" % app_unique_id)
        return {c["objectid"].lower() for c in result.get("value", []) if c.get("objectid")}

    def find(self, entity_set, select, odata_filter):
        """Finds a published record, then falls back to unpublished ones (new app modules and site maps)."""
        query = "?$select=%s&$filter=%s" % (select, odata_filter)
        found = self.dv.first(entity_set + query)
        if found:
            found["_published"] = True
            return found
        result = self.dv.call("GET", entity_set + "/Microsoft.Dynamics.CRM.RetrieveUnpublishedMultiple()" + query)
        values = result.get("value", [])
        return values[0] if values else None

    # ------------------------------------------------------------------ publish

    def publish(self, wr_id, app_id, sitemap_id):
        xml = ("<importexportxml><entities><entity>account</entity><entity>contact</entity></entities>"
               "<webresources><webresource>{%s}</webresource></webresources>"
               "<appmodules><appmodule>{%s}</appmodule></appmodules>"
               "<sitemaps><sitemap>{%s}</sitemap></sitemaps></importexportxml>") % (wr_id, app_id, sitemap_id)
        self.dv.call("POST", "PublishXml", {"ParameterXml": xml})

    # ------------------------------------------------------------------ flows

    def response_properties(self, apis):
        out = {}
        for api in apis:
            found = self.dv.first(("customapis?$select=customapiid&$filter=uniquename eq '%s'"
                                   "&$expand=CustomAPIResponseProperties($select=uniquename),CustomAPIRequestParameters($select=uniquename)") % api)
            if not found:
                sys.exit("Custom API %s was not found in the environment." % api)
            out[api] = {
                "names": [r["uniquename"] for r in found["CustomAPIResponseProperties"]],
                "geocoding": any(r["uniquename"] == "IncludeGeocoding" for r in found["CustomAPIRequestParameters"]),
            }
        return out

    def dataverse_connection(self):
        """A Dataverse connection of the signed-in user, used to turn the flows on in this environment."""
        if self.connection_id:
            return self.connection_id
        refs = self.dv.call("GET", "connectionreferences?$select=connectionid&$filter=contains(connectorid,'shared_commondataserviceforapps') and connectionid ne null").get("value", [])
        counts = {}
        for r in refs:
            counts[r["connectionid"]] = counts.get(r["connectionid"], 0) + 1
        if not counts:
            sys.exit("No Dataverse connection found. Pass --dataverse-connection <connection name>.")
        self.connection_id = max(counts, key=counts.get)
        return self.connection_id

    def ensure_connection_reference(self, p, solution):
        name = flows.connection_reference_name(self.prefix, p)
        existing = self.dv.first("connectionreferences?$select=connectionreferenceid,connectionid&$filter=connectionreferencelogicalname eq '%s'" % name)
        if existing:
            if not existing.get("connectionid"):
                self.dv.call("PATCH", "connectionreferences(%s)" % existing["connectionreferenceid"], {"connectionid": self.dataverse_connection()})
            return name
        print("  creating connection reference %s" % name)
        self.dv.call("POST", "connectionreferences", {
            "connectionreferencelogicalname": name,
            "connectionreferencedisplayname": "%s sample - Dataverse" % p["displayName"],
            "description": "Dataverse connection used by the %s sample verification flows." % p["displayName"],
            "connectorid": flows.API_ID,
            "connectionid": self.dataverse_connection(),
        }, solution=solution)
        return name

    def ensure_flows(self, p, solution):
        v = p["verification"]
        self.ensure_connection_reference(p, solution)
        apis = [v["api"]] + ([v["internationalApi"]] if v.get("internationalApi") else [])
        props = {} if v.get("mode") == "melissaGlobal" else self.response_properties(apis)
        ids = {}
        for table in ("account", "contact"):
            flow_id = stable_id(p["key"], table, "flow")
            ids[table] = flow_id
            body = {
                "name": flows.flow_name(p, table),
                "description": ("Runs when the address of a %s changes: checks it with %s, writes the verified address back to the "
                                "standard address columns, and adds a note with everything %s returned. Part of the %s sample app.") % (
                    table, v["label"], p["displayName"], p["displayName"]),
                "clientdata": flows.clientdata_json(flows.build_flow(p, table, self.prefix, props)),
            }
            existing = self.dv.call("GET", "workflows(%s)?$select=statecode" % flow_id, ok404=True)
            if existing:
                if existing["statecode"] == 1:
                    self.dv.call("PATCH", "workflows(%s)" % flow_id, {"statecode": 0, "statuscode": 1})
                self.dv.call("PATCH", "workflows(%s)" % flow_id, body)
            else:
                print("  creating flow %s" % body["name"])
                body.update({"workflowid": flow_id, "category": 5, "type": 1, "primaryentity": "none"})
                self.dv.call("POST", "workflows", body, solution=solution)
            self.add_to_solution(solution, flow_id, 29)
            try:
                self.dv.call("PATCH", "workflows(%s)" % flow_id, {"statecode": 1, "statuscode": 2})
            except RuntimeError as error:
                print("  warning: flow %s could not be turned on: %s" % (body["name"], error))
        return ids

    # ------------------------------------------------------------------ run

    def build(self, p):
        print("== %s" % p["displayName"])
        publisher_id = self.ensure_publisher()
        solution = self.ensure_solution(p, publisher_id)
        for table in ("account", "contact"):
            for output in p["outputs"]:
                if "column" in output:
                    self.ensure_column(table, p, output, solution)
            if p.get("verification"):
                self.ensure_column(table, p, {
                    "column": "verifiedaddress", "label": "Last Verified Address", "type": "text", "max": 1000, "prop": "",
                    "description": "Address last checked by the %s sample verification flow. The flow uses it to skip its own "
                                   "updates; it reads PENDING while a check is running." % p["displayName"],
                }, solution)
        forms = {table: self.ensure_form(table, p, solution) for table in ("account", "contact")}
        quick_forms = {table: self.ensure_form(table, p, solution, quick_create=True) for table in ("account", "contact")}
        flow_ids = self.ensure_flows(p, solution) if p.get("verification") else None
        wr_id = self.ensure_setup_page(p, forms, quick_forms, solution, flow_ids)
        app_id, sitemap_id = self.ensure_app(p, list(forms.values()) + list(quick_forms.values()), solution)
        print("  publishing")
        self.publish(wr_id, app_id, sitemap_id)
        print("  done: solution %s, app %s" % (solution, app_id))


def solution_name(p):
    return "SharpXrmSample%s" % p["key"]


def config_name(p):
    return "SharpXrmSample_%s" % p["key"]


def setup_page_name(prefix, p):
    return "%s_/%s/setup.html" % (prefix, p["key"].lower())


def app_unique_name(prefix, p):
    return "%s_%sSample" % (prefix, p["key"])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", required=True, help="Environment URL, for example https://yourorg.crm.dynamics.com")
    parser.add_argument("--only", help="Comma-separated provider keys to build (default: all)")
    parser.add_argument("--dataverse-connection", help="Name of the Dataverse connection used to turn the sample flows on "
                                                       "(default: the one most used by connection references in the environment)")
    args = parser.parse_args()

    with open(os.path.join(HERE, "providers.json"), encoding="utf-8") as f:
        catalogue = json.load(f)
    providers = catalogue["providers"]
    if args.only:
        wanted = {k.strip().lower() for k in args.only.split(",")}
        providers = [p for p in providers if p["key"].lower() in wanted]
        if not providers:
            sys.exit("No provider matches --only %s" % args.only)

    builder = Builder(Dataverse(args.env), catalogue)
    builder.connection_id = args.dataverse_connection
    for p in providers:
        builder.build(p)


if __name__ == "__main__":
    main()
