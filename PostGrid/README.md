# PostGrid address autocomplete sample

A ready-to-import model-driven app that shows the **PostGrid** address autocomplete control of SharpXRM Address Validation for Dynamics 365 on Account and Contact forms, including their quick create forms.

## Install

1. Make sure **Address Validation for D365** is installed and licensed in the environment (a trial licence works), using a version of Address Validation for D365 that includes the PostGrid provider.
2. Download [`SharpXrmSamplePostGrid_1_0_0_0_managed.zip`](../dist/SharpXrmSamplePostGrid_1_0_0_0_managed.zip) and import it from **Power Apps > Solutions > Import solution**. When asked, pick (or create) a Microsoft Dataverse connection for the background verification flows.
3. Open the **PostGrid Address Sample** app. It opens on the **Setup** page.
4. Enter your PostGrid public API key, then select **Save and validate**. Also enter the PostGrid secret API key in step 2 for the background verification flows.
5. Select **New sample account** or **New sample contact**, type a street address in **Address search**, and pick a suggestion. **Quick create account** and **Quick create contact** open the same control on the quick create forms (also shown by **+ New** and the **Create** button in the app).
   For example: *1 E 161st St, Bronx*.

## Getting a key

Where to get it: https://docs.postgrid.com/

- Use the public key (live_pk_ or test_pk_) of your PostGrid Address Verification account. The secret key (live_sk_) is for server-side verification only.
- In the PostGrid dashboard, add your Dynamics 365 address (https://yourorg.crm.dynamics.com) to the key's allowed origins.

## What the forms show

| Control output | Column on Account and Contact |
|---|---|
| `street` | Street 1 (`address1_line1`, standard) |
| `unitNumber` | Street 2 (`address1_line2`, standard) |
| `city` | City (`address1_city`, standard) |
| `state` | State/Province (`address1_stateorprovince`, standard) |
| `zip` | ZIP/Postal Code (`address1_postalcode`, standard) |
| `country` | Country/Region (`address1_country`, standard) |
| `fullAddress` | Full Address (`sxs_pg_fulladdress`, sample column) |
| `company` | Company (`sxs_pg_company`, sample column) |
| *(flows)* | Last Verified Address (`sxs_pg_verifiedaddress`, sample column used by the flows) |

## Background verification (Power Automate)

The solution includes two cloud flows, **Verify account address with PostGrid (sample)** and **Verify contact address with PostGrid (sample)**. Each one:

1. Runs when the address of an Account (or Contact) is added or changed.
2. Checks the address with PostGrid Address Verification (US/Canada) and International Address Verification (`sharpxrm_VerifyWithPostGrid` or `sharpxrm_VerifyWithPostGridInternational` outside the US and Canada) through the Microsoft Dataverse connector.
3. Writes the verified address back to the standard address columns (street, unit, city, county, state, ZIP or postal code, country, latitude and longitude).
4. Adds a note to the record with every value the action returned, the address it sent, what it wrote back, and the full raw response. The notes appear in the **Notes** section of the sample forms.

The flows need a **PostGrid secret API key**, entered in step 2 of the Setup page. It is stored in the API Configuration record **SharpXrmSample_PostGrid_Verify**.

To keep them safe in a real environment, the flows only act on records whose address was picked with this sample's control (the *Full Address* sample column is filled). They never touch your other Accounts and Contacts, and several samples can be installed side by side. They also skip their own updates, using the *Last Verified Address* column (it reads `PENDING` while a check is running).

When you import the solution, Power Apps asks for a Microsoft Dataverse connection for the connection reference **PostGrid sample - Dataverse**. Pick or create one and the flows are turned on. Each address change costs one verification call with PostGrid.

## What the solution contains

| Component | Name |
|---|---|
| Solution | `SharpXrmSamplePostGrid` (publisher *SharpXRM Samples*, prefix `sxs`) |
| App | PostGrid Address Sample (`sxs_PostGridSample`) |
| Forms | Account - PostGrid Sample, Contact - PostGrid Sample |
| Quick create forms | Account Quick Create - PostGrid Sample, Contact Quick Create - PostGrid Sample |
| Setup page | `sxs_/postgrid/setup.html` |
| Columns | `sxs_pg_*` on Account and Contact |
| Control | `sharpxrm_PostGridAutocomplete.Autocomplete` (from Address Validation for D365) |
| Flows | Verify account address with PostGrid (sample), Verify contact address with PostGrid (sample) |
| Connection reference | `sxs_postgrid_dataverse` (Microsoft Dataverse) |

The Setup page stores your key in the API Configuration record named **SharpXrmSample_PostGrid**, which the sample forms use. Removing the solution does not delete that record.

The control on the sample forms uses these settings, which you can change in the form designer: `defaultcountry` = `US`, `displaycountries` = `US,CA`, `topcountries` = `US,CA`.

## Source

[`src`](src) holds the unpacked solution (both managed and unmanaged). Rebuild the zips with `pac solution pack --zipfile SharpXrmSamplePostGrid.zip --folder src --packagetype Both`.
