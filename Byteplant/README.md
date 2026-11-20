# Byteplant address autocomplete sample

A ready-to-import model-driven app that shows the **Byteplant** address autocomplete control of SharpXRM Address Validation for Dynamics 365 on Account and Contact forms, including their quick create forms.

## Install

1. Make sure **Address Validation for D365** is installed and licensed in the environment (a trial licence works), using a version of Address Validation for D365 that includes the Byteplant provider.
2. Download [`SharpXrmSampleByteplant_1_0_0_0_managed.zip`](../dist/SharpXrmSampleByteplant_1_0_0_0_managed.zip) and import it from **Power Apps > Solutions > Import solution**. When asked, pick (or create) a Microsoft Dataverse connection for the background verification flows.
3. Open the **Byteplant Address Sample** app. It opens on the **Setup** page.
4. Enter your Byteplant Address Validator API key, then select **Save and validate**.
5. Select **New sample account** or **New sample contact**, type a street address in **Address search**, and pick a suggestion. **Quick create account** and **Quick create contact** open the same control on the quick create forms (also shown by **+ New** and the **Create** button in the app).
   For example: *1600 Amphitheatre Parkway, Mountain View*.

## Getting a key

Where to get it: https://www.address-validator.net/

- Use the API key of your Byteplant Address Validator account. The key never reaches the browser: searches are relayed through Dataverse.

## What the forms show

| Control output | Column on Account and Contact |
|---|---|
| `street` | Street 1 (`address1_line1`, standard) |
| `unitNumber` | Street 2 (`address1_line2`, standard) |
| `city` | City (`address1_city`, standard) |
| `state` | State/Province (`address1_stateorprovince`, standard) |
| `zip` | ZIP/Postal Code (`address1_postalcode`, standard) |
| `country` | Country/Region (`address1_country`, standard) |
| `fullAddress` | Full Address (`sxs_bp_fulladdress`, sample column) |
| `company` | Company (`sxs_bp_company`, sample column) |
| *(flows)* | Last Verified Address (`sxs_bp_verifiedaddress`, sample column used by the flows) |

## Background verification (Power Automate)

The solution includes two cloud flows, **Verify account address with Byteplant (sample)** and **Verify contact address with Byteplant (sample)**. Each one:

1. Runs when the address of an Account (or Contact) is added or changed.
2. Checks the address with Byteplant Address Validator (`sharpxrm_VerifyWithByteplant`) through the Microsoft Dataverse connector.
3. Writes the verified address back to the standard address columns (street, unit, city, county, state, ZIP or postal code, country, latitude and longitude).
4. Adds a note to the record with every value the action returned, the address it sent, what it wrote back, and the full raw response. The notes appear in the **Notes** section of the sample forms.

The flows use the same key as the autocomplete control.

To keep them safe in a real environment, the flows only act on records whose address was picked with this sample's control (the *Full Address* sample column is filled). They never touch your other Accounts and Contacts, and several samples can be installed side by side. They also skip their own updates, using the *Last Verified Address* column (it reads `PENDING` while a check is running).

When you import the solution, Power Apps asks for a Microsoft Dataverse connection for the connection reference **Byteplant sample - Dataverse**. Pick or create one and the flows are turned on. Each address change costs one verification call with Byteplant.

## What the solution contains

| Component | Name |
|---|---|
| Solution | `SharpXrmSampleByteplant` (publisher *SharpXRM Samples*, prefix `sxs`) |
| App | Byteplant Address Sample (`sxs_ByteplantSample`) |
| Forms | Account - Byteplant Sample, Contact - Byteplant Sample |
| Quick create forms | Account Quick Create - Byteplant Sample, Contact Quick Create - Byteplant Sample |
| Setup page | `sxs_/byteplant/setup.html` |
| Columns | `sxs_bp_*` on Account and Contact |
| Control | `sharpxrm_ByteplantAutocomplete.Autocomplete` (from Address Validation for D365) |
| Flows | Verify account address with Byteplant (sample), Verify contact address with Byteplant (sample) |
| Connection reference | `sxs_byteplant_dataverse` (Microsoft Dataverse) |

The Setup page stores your key in the API Configuration record named **SharpXrmSample_Byteplant**, which the sample forms use. Removing the solution does not delete that record.

The control on the sample forms uses these settings, which you can change in the form designer: `defaultcountry` = `US`, `topcountries` = `US,CA,GB,AU`.

## Source

[`src`](src) holds the unpacked solution (both managed and unmanaged). Rebuild the zips with `pac solution pack --zipfile SharpXrmSampleByteplant.zip --folder src --packagetype Both`.
