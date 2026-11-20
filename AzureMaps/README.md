# Azure Maps address autocomplete sample

A ready-to-import model-driven app that shows the **Azure Maps** address autocomplete control of SharpXRM Address Validation for Dynamics 365 on Account and Contact forms, including their quick create forms.

## Install

1. Make sure **Address Validation for D365** is installed and licensed in the environment (a trial licence works).
2. Download [`SharpXrmSampleAzureMaps_1_0_0_0_managed.zip`](../dist/SharpXrmSampleAzureMaps_1_0_0_0_managed.zip) and import it from **Power Apps > Solutions > Import solution**. When asked, pick (or create) a Microsoft Dataverse connection for the background verification flows.
3. Open the **Azure Maps Address Sample** app. It opens on the **Setup** page.
4. Enter your Azure Maps subscription key, then select **Save and validate**.
5. Select **New sample account** or **New sample contact**, type a street address in **Address search**, and pick a suggestion. **Quick create account** and **Quick create contact** open the same control on the quick create forms (also shown by **+ New** and the **Create** button in the app).
   For example: *500 Pine St, Seattle*.

## Getting a key

Where to get it: https://learn.microsoft.com/azure/azure-maps/how-to-manage-authentication

- In the Azure portal, open your Azure Maps account, then Authentication, and copy the Primary Key.

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
| `fullAddress` | Full Address (`sxs_az_fulladdress`, sample column) |
| `municipality` | Municipality (`sxs_az_municipality`, sample column) |
| *(flows)* | Last Verified Address (`sxs_az_verifiedaddress`, sample column used by the flows) |

## Background verification (Power Automate)

The solution includes two cloud flows, **Verify account address with Azure Maps (sample)** and **Verify contact address with Azure Maps (sample)**. Each one:

1. Runs when the address of an Account (or Contact) is added or changed.
2. Checks the address with Azure Maps address search (`sharpxrm_VerifyWithAzureMaps`) through the Microsoft Dataverse connector.
3. Writes the verified address back to the standard address columns (street, unit, city, county, state, ZIP or postal code, country, latitude and longitude).
4. Adds a note to the record with every value the action returned, the address it sent, what it wrote back, and the full raw response. The notes appear in the **Notes** section of the sample forms.

The flows use the same key as the autocomplete control.

To keep them safe in a real environment, the flows only act on records whose address was picked with this sample's control (the *Full Address* sample column is filled). They never touch your other Accounts and Contacts, and several samples can be installed side by side. They also skip their own updates, using the *Last Verified Address* column (it reads `PENDING` while a check is running).

When you import the solution, Power Apps asks for a Microsoft Dataverse connection for the connection reference **Azure Maps sample - Dataverse**. Pick or create one and the flows are turned on. Each address change costs one verification call with Azure Maps.

## What the solution contains

| Component | Name |
|---|---|
| Solution | `SharpXrmSampleAzureMaps` (publisher *SharpXRM Samples*, prefix `sxs`) |
| App | Azure Maps Address Sample (`sxs_AzureMapsSample`) |
| Forms | Account - Azure Maps Sample, Contact - Azure Maps Sample |
| Quick create forms | Account Quick Create - Azure Maps Sample, Contact Quick Create - Azure Maps Sample |
| Setup page | `sxs_/azuremaps/setup.html` |
| Columns | `sxs_az_*` on Account and Contact |
| Control | `sharpxrm_AzureMapsAutocomplete.Autocomplete` (from Address Validation for D365) |
| Flows | Verify account address with Azure Maps (sample), Verify contact address with Azure Maps (sample) |
| Connection reference | `sxs_azuremaps_dataverse` (Microsoft Dataverse) |

The Setup page stores your key in the API Configuration record named **SharpXrmSample_AzureMaps**, which the sample forms use. Removing the solution does not delete that record.

The control on the sample forms uses these settings, which you can change in the form designer: `defaultcountry` = `US`, `topcountries` = `US,CA,GB`.

## Source

[`src`](src) holds the unpacked solution (both managed and unmanaged). Rebuild the zips with `pac solution pack --zipfile SharpXrmSampleAzureMaps.zip --folder src --packagetype Both`.
