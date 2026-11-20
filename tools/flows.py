"""Power Automate flow definitions for the sample apps.

Each provider with a "verification" block in providers.json gets two cloud flows, one for Account and
one for Contact. They run when an address column changes and:
  1. mark the row as being verified (so their own write-back does not start them again),
  2. call the provider's verification action through the Microsoft Dataverse connector,
  3. write the verified address back to the standard address columns,
  4. add a note to the row with every value the action returned, plus the raw response.
"""
import json

CONNECTOR = "shared_commondataserviceforapps"
API_ID = "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps"
PENDING = "PENDING"

# (key in the composed address, standard column, label in the note)
ADDRESS = [
    ("line1", "address1_line1", "Street"),
    ("line2", "address1_line2", "Unit"),
    ("city", "address1_city", "City"),
    ("county", "address1_county", "County"),
    ("state", "address1_stateorprovince", "State/Province"),
    ("zip", "address1_postalcode", "ZIP/Postal code"),
    ("country", "address1_country", "Country"),
]
PROPERTY_ORDER = [
    "ResultFound", "VerificationStatus", "Confidence", "MissingComponents", "VerificationDetails", "EntityType",
    "StreetAddress", "UnitNumber", "City", "County", "State", "ZipPostalCode", "ExtendedZipPostalCode", "Country",
    "FullAddress", "Latitude", "Longitude",
]
MELISSA_PROPERTIES = ["ValidationStatus", "OperationResultMessage", "TransmissionResults", "TransmissionReference", "ValidationResults"]
TABLES = {"account": ("accounts", "accountid", "Account"), "contact": ("contacts", "contactid", "Contact")}
NL = "decodeUriComponent('%0A')"


def verify_config_name(p):
    v = p["verification"]
    return "SharpXrmSample_%s" % p["key"] if v["config"] == "sample" else "SharpXrmSample_%s_Verify" % p["key"]


def field_mapping_name(p, table):
    return "SharpXrmSample_%s_%s" % (p["key"], table)


def fingerprint_column(prefix, p):
    return "%s_%s_verifiedaddress" % (prefix, p["code"])


def owner_column(prefix, p):
    """Sample column the provider's control always fills; marks rows whose address came from this sample."""
    return "%s_%s_fulladdress" % (prefix, p["code"])


def connection_reference_name(prefix, p):
    return "%s_%s_dataverse" % (prefix, p["key"].lower())


def flow_name(p, table):
    return "Verify %s address with %s (sample)" % (TABLES[table][2].lower(), p["displayName"])


def order_properties(names):
    known = [n for n in PROPERTY_ORDER if n in names]
    return known + sorted(n for n in names if n not in PROPERTY_ORDER)


def _trigger(column):
    return "triggerOutputs()?['body/%s']" % column


def _fingerprint(expressions):
    return "concat(%s)" % ",'|',".join("coalesce(%s,'')" % e for e in expressions)


def _host(operation):
    return {"connectionName": CONNECTOR, "operationId": operation, "apiId": API_ID}


def _op(operation, parameters, run_after=None):
    return {
        "type": "OpenApiConnection",
        "inputs": {"host": _host(operation), "parameters": parameters, "authentication": "@parameters('$authentication')"},
        "runAfter": run_after or {},
    }


def _after(*names, statuses=("Succeeded",)):
    return {n: list(statuses) for n in names}


def build_flow(p, table, prefix, response_properties):
    """Returns the clientdata dictionary of the flow for one table."""
    v = p["verification"]
    entity_set, key, table_label = TABLES[table]
    fp_col = fingerprint_column(prefix, p)
    record_id = "@%s" % _trigger(key)
    trigger_fp = _fingerprint([_trigger(c) for _, c, _ in ADDRESS])
    stored_fp = "coalesce(%s,'')" % _trigger(fp_col)
    provider = p["displayName"]

    trigger = {
        "When_an_address_is_added_or_changed": {
            "type": "OpenApiConnectionWebhook",
            "inputs": {
                "host": _host("SubscribeWebhookTrigger"),
                "parameters": {
                    "subscriptionRequest/message": 4,
                    "subscriptionRequest/entityname": table,
                    "subscriptionRequest/scope": 4,
                    "subscriptionRequest/filteringattributes": ",".join(c for _, c, _ in ADDRESS),
                },
                "authentication": "@parameters('$authentication')",
            },
            # Only rows whose address was picked with this sample's control (its Full Address column is filled), so the
            # flows never touch other records and several samples can live side by side. Then skip rows without a
            # street, rows already being verified, and the flow's own write-back.
            "conditions": [{
                "expression": "@and(not(empty(coalesce(%s,''))), not(empty(coalesce(%s,''))), not(equals(%s,'%s')), not(equals(%s,%s)))" % (
                    _trigger(owner_column(prefix, p)), _trigger("address1_line1"), stored_fp, PENDING, stored_fp, trigger_fp)
            }],
        }
    }

    actions = {
        "Initialize_result": {
            "type": "InitializeVariable",
            "inputs": {"variables": [{"name": "Result", "type": "object", "value": {}}]},
            "runAfter": {},
        },
        "Mark_as_being_verified": _op("UpdateRecord", {
            "entityName": entity_set, "recordId": record_id, "item/%s" % fp_col: PENDING,
        }, _after("Initialize_result")),
        "Find_API_configuration": _op("ListRecords", {
            "entityName": "sharpxrm_sharpxrmconfigurations",
            "$select": "sharpxrm_sharpxrmconfigurationid",
            "$filter": "sharpxrm_name eq '%s'" % verify_config_name(p),
            "$top": 1,
        }, _after("Mark_as_being_verified")),
    }
    config_id = "@first(outputs('Find_API_configuration')?['body/value'])?['sharpxrm_sharpxrmconfigurationid']"

    sent_lines = "".join("%s: @{%s}\n" % (label, _trigger(col)) for _, col, label in ADDRESS)

    if v.get("mode") == "melissaGlobal":
        actions["Find_field_mapping"] = _op("ListRecords", {
            "entityName": "sharpxrm_addressvalidationfieldsconfigs",
            "$select": "sharpxrm_addressvalidationfieldsconfigid",
            "$filter": "sharpxrm_configurationname eq '%s'" % field_mapping_name(p, table),
            "$top": 1,
        }, _after("Find_API_configuration"))
        scope_after = _after("Find_field_mapping")
        scope = _melissa_scope(p, table, entity_set, key, record_id, fp_col, sent_lines)
    else:
        scope_after = _after("Find_API_configuration")
        scope = _verify_scope(p, table, entity_set, key, record_id, fp_col, config_id, sent_lines, trigger_fp, response_properties)

    actions["Verify"] = {"type": "Scope", "actions": scope, "runAfter": scope_after}
    actions["If_verification_failed"] = {
        "type": "Scope",
        "runAfter": _after("Verify", statuses=("Failed", "TimedOut")),
        "actions": {
            "Clear_the_marker": _op("UpdateRecord", {
                "entityName": entity_set, "recordId": record_id, "item/%s" % fp_col: "",
            }),
            "Add_a_failure_note": _op("CreateRecord", {
                "entityName": "annotations",
                "item/subject": "Address verification failed (%s)" % provider,
                "item/notetext": (
                    "The %s verification flow could not check this address on @{utcNow()}.\n"
                    "Check that the key is saved on the sample app's Setup page and that your licence covers %s.\n\n"
                    "Address sent\n%s\nDetails\n@{take(string(result('Verify')), 90000)}") % (provider, p["licenceName"], sent_lines),
                "item/objectid_%s@odata.bind" % table: "/%s(@{%s})" % (entity_set, _trigger(key)),
            }, _after("Clear_the_marker", statuses=("Succeeded", "Failed"))),
        },
    }

    definition = {
        "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {
            "$connections": {"defaultValue": {}, "type": "Object"},
            "$authentication": {"defaultValue": {}, "type": "SecureObject"},
        },
        "triggers": trigger,
        "actions": actions,
        "outputs": {},
    }
    return {
        "properties": {
            "connectionReferences": {
                CONNECTOR: {
                    "runtimeSource": "embedded",
                    "connection": {"connectionReferenceLogicalName": connection_reference_name(prefix, p)},
                    "api": {"name": CONNECTOR},
                }
            },
            "definition": definition,
            "templateName": "",
        },
        "schemaVersion": "1.0.0.0",
    }


def _verify_call(api, table, key, config_id, geocoding_param):
    params = {
        "actionName": api,
        "item/APIConfiguration": {
            "@@odata.type": "Microsoft.Dynamics.CRM.sharpxrm_sharpxrmconfiguration",
            "sharpxrm_sharpxrmconfigurationid": config_id,
        },
        "item/InputStreetAddress": "@%s" % _trigger("address1_line1"),
        "item/InputUnitNumber": "@%s" % _trigger("address1_line2"),
        "item/InputCity": "@%s" % _trigger("address1_city"),
        "item/InputCounty": "@%s" % _trigger("address1_county"),
        "item/InputState": "@%s" % _trigger("address1_stateorprovince"),
        "item/InputZipPostalCode": "@%s" % _trigger("address1_postalcode"),
        "item/InputCountry": "@%s" % _trigger("address1_country"),
        "item/RecordLogicalName": table,
        "item/RecordId": "@{%s}" % _trigger(key),
    }
    if geocoding_param:
        params["item/IncludeGeocoding"] = False
    return params


def _verify_scope(p, table, entity_set, key, record_id, fp_col, config_id, sent_lines, trigger_fp, response_properties):
    v = p["verification"]
    provider = p["displayName"]
    result = "variables('Result')"
    scope = {}

    def call(name, api, run_after):
        props = response_properties[api]
        scope[name] = _op("PerformUnboundAction", _verify_call(api, table, key, config_id, props.get("geocoding")), run_after)

    if v.get("internationalApi"):
        countries = ",".join("'%s'" % c for c in v["domesticCountries"])
        domestic = "@contains(createArray(%s), toLower(trim(coalesce(%s,''))))" % (countries, _trigger("address1_country"))
        branch_yes, branch_no = {}, {}
        for target, api, name in ((branch_yes, v["api"], "Verify_domestic_address"), (branch_no, v["internationalApi"], "Verify_international_address")):
            target[name] = _op("PerformUnboundAction",
                               _verify_call(api, table, key, config_id, response_properties[api].get("geocoding")))
            target["Keep_%s_result" % name.split("_")[1]] = {
                "type": "SetVariable", "inputs": {"name": "Result", "value": "@body('%s')" % name}, "runAfter": _after(name)}
        scope["Choose_the_verification_API"] = {
            "type": "If",
            "expression": {"and": [{"equals": [domestic, True]}]},
            "actions": branch_yes,
            "else": {"actions": branch_no},
            "runAfter": {},
        }
        last = "Choose_the_verification_API"
        api_names = "%s (US%s) or %s" % (v["api"], "/Canada" if "canada" in v["domesticCountries"] else "", v["internationalApi"])
        props = order_properties(set(response_properties[v["api"]]["names"]) | set(response_properties[v["internationalApi"]]["names"]))
    else:
        call("Verify_the_address", v["api"], {})
        scope["Keep_the_result"] = {
            "type": "SetVariable", "inputs": {"name": "Result", "value": "@body('Verify_the_address')"},
            "runAfter": _after("Verify_the_address")}
        last = "Keep_the_result"
        api_names = v["api"]
        props = order_properties(response_properties[v["api"]]["names"])

    def pick(prop, column):
        return "@if(empty(%s?['%s']), %s, %s?['%s'])" % (result, prop, _trigger(column), result, prop)

    zip_expr = ("@if(empty({r}?['ZipPostalCode']), {t}, if(empty({r}?['ExtendedZipPostalCode']), {r}?['ZipPostalCode'], "
                "if(contains({r}?['ExtendedZipPostalCode'],'-'), {r}?['ExtendedZipPostalCode'], "
                "concat({r}?['ZipPostalCode'],'-',{r}?['ExtendedZipPostalCode']))))").format(r=result, t=_trigger("address1_postalcode"))

    def coordinate(prop, column):
        return "@if(equals(float(coalesce(%s?['%s'],0)),float(0)), %s, %s?['%s'])" % (result, prop, _trigger(column), result, prop)

    scope["New_address"] = {
        "type": "Compose",
        "inputs": {
            "line1": pick("StreetAddress", "address1_line1"),
            "line2": pick("UnitNumber", "address1_line2"),
            "city": pick("City", "address1_city"),
            "county": pick("County", "address1_county"),
            "state": pick("State", "address1_stateorprovince"),
            "zip": zip_expr,
            "country": pick("Country", "address1_country"),
            "latitude": coordinate("Latitude", "address1_latitude"),
            "longitude": coordinate("Longitude", "address1_longitude"),
        },
        "runAfter": _after(last),
    }
    new = lambda k: "outputs('New_address')?['%s']" % k
    update = {"entityName": entity_set, "recordId": record_id}
    for k, col, _ in ADDRESS:
        update["item/%s" % col] = "@%s" % new(k)
    update["item/address1_latitude"] = "@%s" % new("latitude")
    update["item/address1_longitude"] = "@%s" % new("longitude")
    update["item/%s" % fp_col] = "@%s" % _fingerprint([new(k) for k, _, _ in ADDRESS])
    scope["Was_a_match_found"] = {
        "type": "If",
        "expression": {"and": [{"equals": ["@%s?['ResultFound']" % result, "Success"]}]},
        "actions": {"Write_the_verified_address": _op("UpdateRecord", update)},
        "else": {"actions": {"Remember_the_checked_address": _op("UpdateRecord", {
            "entityName": entity_set, "recordId": record_id, "item/%s" % fp_col: "@%s" % trigger_fp})}},
        "runAfter": _after("New_address"),
    }

    result_lines = "".join("%s: @{%s?['%s']}\n" % (n, result, n) for n in props)
    written = "@{if(equals(%s?['ResultFound'],'Success'), concat(%s), 'Nothing was written back because %s found no match.')}" % (
        result,
        ", ".join("'%s: ', coalesce(string(%s),''), %s" % (label, new(k), NL) for k, _, label in ADDRESS)
        + ", 'Latitude: ', string(%s), %s, 'Longitude: ', string(%s)" % (new("latitude"), NL, new("longitude")),
        provider)
    scope["Add_a_note_with_the_full_result"] = _op("CreateRecord", {
        "entityName": "annotations",
        "item/subject": "Address verification (%s): @{%s?['ResultFound']} @{%s?['VerificationStatus']}" % (provider, result, result),
        "item/notetext": (
            "%s checked this address on @{utcNow()} using %s.\n\n"
            "Address sent\n%s\n"
            "Result returned by %s\n%s\n"
            "Written back to the address\n%s\n\n"
            "Full response\n@{string(%s)}") % (provider, api_names, sent_lines, provider, result_lines, written, result),
        "item/objectid_%s@odata.bind" % table: "/%s(@{%s})" % (entity_set, _trigger(key)),
    }, _after("Was_a_match_found"))
    return scope


def _melissa_scope(p, table, entity_set, key, record_id, fp_col, sent_lines):
    provider = p["displayName"]
    result = "variables('Result')"
    mapping_id = "@first(outputs('Find_field_mapping')?['body/value'])?['sharpxrm_addressvalidationfieldsconfigid']"
    columns = [c for _, c, _ in ADDRESS] + ["address1_latitude", "address1_longitude"]
    row = lambda c: "outputs('Read_the_updated_address')?['body/%s']" % c
    scope = {
        "Verify_the_address": _op("PerformUnboundAction", {
            "actionName": p["verification"]["api"],
            "item/Target": {"@@odata.type": "Microsoft.Dynamics.CRM.%s" % table, key: "@%s" % _trigger(key)},
            "item/FieldMappingId": {
                "@@odata.type": "Microsoft.Dynamics.CRM.sharpxrm_addressvalidationfieldsconfig",
                "sharpxrm_addressvalidationfieldsconfigid": mapping_id,
            },
        }),
    }
    scope["Keep_the_result"] = {
        "type": "SetVariable", "inputs": {"name": "Result", "value": "@body('Verify_the_address')"},
        "runAfter": _after("Verify_the_address")}
    scope["Read_the_updated_address"] = _op("GetItem", {
        "entityName": entity_set, "recordId": record_id, "$select": ",".join(columns),
    }, _after("Keep_the_result"))
    scope["Remember_the_checked_address"] = _op("UpdateRecord", {
        "entityName": entity_set, "recordId": record_id,
        "item/%s" % fp_col: "@%s" % _fingerprint([row(c) for _, c, _ in ADDRESS]),
    }, _after("Read_the_updated_address"))
    result_lines = "".join("%s: @{%s?['%s']}\n" % (n, result, n) for n in MELISSA_PROPERTIES)
    after_lines = "".join("%s: @{%s}\n" % (label, row(c)) for _, c, label in ADDRESS)
    after_lines += "Latitude: @{%s}\nLongitude: @{%s}\n" % (row("address1_latitude"), row("address1_longitude"))
    scope["Add_a_note_with_the_full_result"] = _op("CreateRecord", {
        "entityName": "annotations",
        "item/subject": "Address verification (%s): @{%s?['ValidationStatus']}" % (provider, result),
        "item/notetext": (
            "%s checked this address on @{utcNow()} using Melissa Global Address Verification (%s). "
            "The action writes the verified address back through the Field Mapping %s.\n\n"
            "Address sent\n%s\n"
            "Result returned by Melissa\n%s\n"
            "Address after verification\n%s\n"
            "Full response\n@{string(%s)}") % (
            provider, p["verification"]["api"], field_mapping_name(p, table), sent_lines, result_lines, after_lines, result),
        "item/objectid_%s@odata.bind" % table: "/%s(@{%s})" % (entity_set, _trigger(key)),
    }, _after("Remember_the_checked_address"))
    return scope


def clientdata_json(clientdata):
    return json.dumps(clientdata, separators=(",", ":"))
