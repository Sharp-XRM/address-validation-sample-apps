# Melissa Express Entry address autocomplete sample

A ready-to-import model-driven app that shows the **Melissa Express Entry** address autocomplete control of SharpXRM Address Validation for Dynamics 365 on Account and Contact forms, including their quick create forms.

## Install

1. Make sure **Address Validation for D365** is installed and licensed in the environment (a trial licence works), using a version of Address Validation for D365 whose Melissa Express Entry control is 0.2.0 or later (it adds the Country Subdivision Code output).
2. Download [`SharpXrmSampleMelissaExpressEntry_1_0_0_0_managed.zip`](../dist/SharpXrmSampleMelissaExpressEntry_1_0_0_0_managed.zip) and import it from **Power Apps > Solutions > Import solution**. When asked, pick (or create) a Microsoft Dataverse connection for the background verification flows.
3. Open the **Melissa Express Entry Address Sample** app. It opens on the **Setup** page.
4. Enter your Melissa licence key, then select **Save and validate**.
5. Select **New sample account** or **New sample contact**, type a street address in **Address search**, and pick a suggestion. **Quick create account** and **Quick create contact** open the same control on the quick create forms (also shown by **+ New** and the **Create** button in the app).
   For example: *799 Greenwich St, New York (then open the building row with several addresses to pick a unit)*.

## Getting a key

Where to get it: https://docs.melissa.com/cloud-api/global-express-entry/global-express-entry-quickstart.html

- Use a Melissa licence key that has Global Express Entry credits.

## What the forms show

| Control output | Column on Account and Contact |
|---|---|
| `street` | Street 1 (`address1_line1`, standard) |
| `unitNumber` | Street 2 (`address1_line2`, standard) |
| `city` | City (`address1_city`, standard) |
| `county` | County (`address1_county`, standard) |
| `state` | State/Province (`address1_stateorprovince`, standard) |
| `zip` | ZIP/Postal Code (`address1_postalcode`, standard) |
| `country` | Country/Region (`address1_country`, standard) |
| `latitude` | Latitude (`address1_latitude`, standard) |
| `longitude` | Longitude (`address1_longitude`, standard) |
| `fullAddress` | Full Address (`sxs_ee_fulladdress`, sample column) |
| `building` | Building (`sxs_ee_building`, sample column) |
| `organization` | Organization (`sxs_ee_organization`, sample column) |
| `dependentLocality` | Dependent Locality (`sxs_ee_dependentlocality`, sample column) |
| `subdivisionCode` | Country Subdivision Code (ISO 3166-2) (`sxs_ee_subdivisioncode`, sample column) |
| *(flows)* | Last Verified Address (`sxs_ee_verifiedaddress`, sample column used by the flows) |

## Background verification (Power Automate)

The solution includes two cloud flows, **Verify account address with Melissa Express Entry (sample)** and **Verify contact address with Melissa Express Entry (sample)**. Each one:

1. Runs when the address of an Account (or Contact) is added or changed.
2. Checks the address with Melissa Global Address Verification (`sharpxrm_GlobalPersonator`) through the Microsoft Dataverse connector.
3. Writes the verified address back to the standard address columns (street, unit, city, county, state, ZIP or postal code, country, latitude and longitude).
4. Adds a note to the record with every value the action returned, the address it sent, what it wrote back, and the full raw response. The notes appear in the **Notes** section of the sample forms.

The flows use the same Melissa licence key with **Melissa Global Address Verification**. When you save the key, the Setup page also creates the API Configuration **SharpXrmSample_MelissaExpressEntry_Verify** and the Field Mappings **SharpXrmSample_MelissaExpressEntry_account** and **SharpXrmSample_MelissaExpressEntry_contact** that the flows use.

To keep them safe in a real environment, the flows only act on records whose address was picked with this sample's control (the *Full Address* sample column is filled). They never touch your other Accounts and Contacts, and several samples can be installed side by side. They also skip their own updates, using the *Last Verified Address* column (it reads `PENDING` while a check is running).

When you import the solution, Power Apps asks for a Microsoft Dataverse connection for the connection reference **Melissa Express Entry sample - Dataverse**. Pick or create one and the flows are turned on. Each address change costs one verification call with Melissa Express Entry.

## What the solution contains

| Component | Name |
|---|---|
| Solution | `SharpXrmSampleMelissaExpressEntry` (publisher *SharpXRM Samples*, prefix `sxs`) |
| App | Melissa Express Entry Address Sample (`sxs_MelissaExpressEntrySample`) |
| Forms | Account - Melissa Express Entry Sample, Contact - Melissa Express Entry Sample |
| Quick create forms | Account Quick Create - Melissa Express Entry Sample, Contact Quick Create - Melissa Express Entry Sample |
| Setup page | `sxs_/melissaexpressentry/setup.html` |
| Columns | `sxs_ee_*` on Account and Contact |
| Control | `sharpxrm_ExpressEntry.Autocomplete` (from Address Validation for D365) |
| Flows | Verify account address with Melissa Express Entry (sample), Verify contact address with Melissa Express Entry (sample) |
| Connection reference | `sxs_melissaexpressentry_dataverse` (Microsoft Dataverse) |

The Setup page stores your key in the API Configuration record named **SharpXrmSample_MelissaExpressEntry**, which the sample forms use. Removing the solution does not delete that record.

The control on the sample forms uses these settings, which you can change in the form designer: `defaultcountry` = `US`, `topcountries` = `US,CA,MX,GB`.

## Source

[`src`](src) holds the unpacked solution (both managed and unmanaged). Rebuild the zips with `pac solution pack --zipfile SharpXrmSampleMelissaExpressEntry.zip --folder src --packagetype Both`.
