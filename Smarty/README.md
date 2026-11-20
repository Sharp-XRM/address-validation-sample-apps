# Smarty address autocomplete sample

A ready-to-import model-driven app that shows the **Smarty** address autocomplete control of SharpXRM Address Validation for Dynamics 365 on Account and Contact forms, including their quick create forms.

## Install

1. Make sure **Address Validation for D365** is installed and licensed in the environment (a trial licence works), using a version of Address Validation for D365 that includes the Smarty provider.
2. Download [`SharpXrmSampleSmarty_1_0_0_0_managed.zip`](../dist/SharpXrmSampleSmarty_1_0_0_0_managed.zip) and import it from **Power Apps > Solutions > Import solution**. When asked, pick (or create) a Microsoft Dataverse connection for the background verification flows.
3. Open the **Smarty Address Sample** app. It opens on the **Setup** page.
4. Enter your Smarty embedded key, then select **Save and validate**. Also enter the Smarty secret key in step 2 for the background verification flows.
5. Select **New sample account** or **New sample contact**, type a street address in **Address search**, and pick a suggestion. **Quick create account** and **Quick create contact** open the same control on the quick create forms (also shown by **+ New** and the **Create** button in the app).
   For example: *1600 Amphitheatre Pkwy, Mountain View*.

## Getting a key

Where to get it: https://www.smarty.com/docs/cloud/authentication

- Use an embedded key (website key). Secret keys (Auth ID:Auth Token) are for server-side verification only.
- In your Smarty account, add your Dynamics 365 host (yourorg.crm.dynamics.com) to the embedded key's authorised hosts.
- US suggestions need a US Autocomplete Pro subscription; other countries need International Address Autocomplete.

## What the forms show

| Control output | Column on Account and Contact |
|---|---|
| `street` | Street 1 (`address1_line1`, standard) |
| `unitNumber` | Street 2 (`address1_line2`, standard) |
| `city` | City (`address1_city`, standard) |
| `state` | State/Province (`address1_stateorprovince`, standard) |
| `zip` | ZIP/Postal Code (`address1_postalcode`, standard) |
| `country` | Country/Region (`address1_country`, standard) |
| `fullAddress` | Full Address (`sxs_sm_fulladdress`, sample column) |
| `company` | Company (`sxs_sm_company`, sample column) |
| *(flows)* | Last Verified Address (`sxs_sm_verifiedaddress`, sample column used by the flows) |

## Background verification (Power Automate)

The solution includes two cloud flows, **Verify account address with Smarty (sample)** and **Verify contact address with Smarty (sample)**. Each one:

1. Runs when the address of an Account (or Contact) is added or changed.
2. Checks the address with Smarty US Street Address and International Street Address (`sharpxrm_VerifyWithSmarty` or `sharpxrm_VerifyWithSmartyInternational` outside the US) through the Microsoft Dataverse connector.
3. Writes the verified address back to the standard address columns (street, unit, city, county, state, ZIP or postal code, country, latitude and longitude).
4. Adds a note to the record with every value the action returned, the address it sent, what it wrote back, and the full raw response. The notes appear in the **Notes** section of the sample forms.

The flows need a **Smarty secret key**, entered in step 2 of the Setup page. It is stored in the API Configuration record **SharpXrmSample_Smarty_Verify**.

To keep them safe in a real environment, the flows only act on records whose address was picked with this sample's control (the *Full Address* sample column is filled). They never touch your other Accounts and Contacts, and several samples can be installed side by side. They also skip their own updates, using the *Last Verified Address* column (it reads `PENDING` while a check is running).

When you import the solution, Power Apps asks for a Microsoft Dataverse connection for the connection reference **Smarty sample - Dataverse**. Pick or create one and the flows are turned on. Each address change costs one verification call with Smarty.

## What the solution contains

| Component | Name |
|---|---|
| Solution | `SharpXrmSampleSmarty` (publisher *SharpXRM Samples*, prefix `sxs`) |
| App | Smarty Address Sample (`sxs_SmartySample`) |
| Forms | Account - Smarty Sample, Contact - Smarty Sample |
| Quick create forms | Account Quick Create - Smarty Sample, Contact Quick Create - Smarty Sample |
| Setup page | `sxs_/smarty/setup.html` |
| Columns | `sxs_sm_*` on Account and Contact |
| Control | `sharpxrm_SmartyAutocomplete.Autocomplete` (from Address Validation for D365) |
| Flows | Verify account address with Smarty (sample), Verify contact address with Smarty (sample) |
| Connection reference | `sxs_smarty_dataverse` (Microsoft Dataverse) |

The Setup page stores your key in the API Configuration record named **SharpXrmSample_Smarty**, which the sample forms use. Removing the solution does not delete that record.

The control on the sample forms uses these settings, which you can change in the form designer: `defaultcountry` = `US`, `topcountries` = `US,CA,GB`.

## Source

[`src`](src) holds the unpacked solution (both managed and unmanaged). Rebuild the zips with `pac solution pack --zipfile SharpXrmSampleSmarty.zip --folder src --packagetype Both`.
