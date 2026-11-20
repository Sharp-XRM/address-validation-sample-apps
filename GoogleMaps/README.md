# Google Maps address autocomplete sample

A ready-to-import model-driven app that shows the **Google Maps** address autocomplete control of SharpXRM Address Validation for Dynamics 365 on Account and Contact forms, including their quick create forms.

## Install

1. Make sure **Address Validation for D365** is installed and licensed in the environment (a trial licence works).
2. Download [`SharpXrmSampleGoogleMaps_1_0_0_0_managed.zip`](../dist/SharpXrmSampleGoogleMaps_1_0_0_0_managed.zip) and import it from **Power Apps > Solutions > Import solution**. When asked, pick (or create) a Microsoft Dataverse connection for the background verification flows.
3. Open the **Google Maps Address Sample** app. It opens on the **Setup** page.
4. Enter your Google Maps API key, then select **Save and validate**.
5. Select **New sample account** or **New sample contact**, type a street address in **Address search**, and pick a suggestion. **Quick create account** and **Quick create contact** open the same control on the quick create forms (also shown by **+ New** and the **Create** button in the app).
   For example: *1600 Amphitheatre Parkway, Mountain View*.

## Getting a key

Where to get it: https://developers.google.com/maps/documentation/places/web-service/get-api-key

- Create the key in the Google Cloud console and enable the Places API (New) and the Geocoding API for it.
- Restrict the key to your Dynamics 365 address, for example https://yourorg.crm.dynamics.com/*.

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
| `fullAddress` | Full Address (`sxs_gm_fulladdress`, sample column) |
| `PostalTown` | Postal Town (`sxs_gm_postaltown`, sample column) |
| `AdminLevel3` | Admin Area Level 3 (`sxs_gm_adminlevel3`, sample column) |
| `AdminLevel4` | Admin Area Level 4 (`sxs_gm_adminlevel4`, sample column) |
| `AdminLevel5` | Admin Area Level 5 (`sxs_gm_adminlevel5`, sample column) |
| `AdminLevel6` | Admin Area Level 6 (`sxs_gm_adminlevel6`, sample column) |
| `placesBusinessName` | Business Name (`sxs_gm_businessname`, sample column) |
| `placeBusinessStatus` | Business Status (`sxs_gm_businessstatus`, sample column) |
| `placesPhoneNumber` | Business Phone (`sxs_gm_businessphone`, sample column) |
| `placesBusinessURL` | Business Website (`sxs_gm_businesswebsite`, sample column) |
| `placesGoogleMapsURL` | Google Maps Link (`sxs_gm_googlemapsurl`, sample column) |
| `placesVicinity` | Vicinity (`sxs_gm_vicinity`, sample column) |
| `placesTypes` | Place Types (`sxs_gm_placetypes`, sample column) |
| `placesEditorialSummary` | Editorial Summary (`sxs_gm_editorialsummary`, sample column) |
| *(flows)* | Last Verified Address (`sxs_gm_verifiedaddress`, sample column used by the flows) |

## Background verification (Power Automate)

The solution includes two cloud flows, **Verify account address with Google Maps (sample)** and **Verify contact address with Google Maps (sample)**. Each one:

1. Runs when the address of an Account (or Contact) is added or changed.
2. Checks the address with Google Address Validation (`sharpxrm_VerifyWithGoogleAddressValidation`) through the Microsoft Dataverse connector.
3. Writes the verified address back to the standard address columns (street, unit, city, county, state, ZIP or postal code, country, latitude and longitude).
4. Adds a note to the record with every value the action returned, the address it sent, what it wrote back, and the full raw response. The notes appear in the **Notes** section of the sample forms.

The flows use the same key as the autocomplete control.

To keep them safe in a real environment, the flows only act on records whose address was picked with this sample's control (the *Full Address* sample column is filled). They never touch your other Accounts and Contacts, and several samples can be installed side by side. They also skip their own updates, using the *Last Verified Address* column (it reads `PENDING` while a check is running).

When you import the solution, Power Apps asks for a Microsoft Dataverse connection for the connection reference **Google Maps sample - Dataverse**. Pick or create one and the flows are turned on. Each address change costs one verification call with Google Maps.

## What the solution contains

| Component | Name |
|---|---|
| Solution | `SharpXrmSampleGoogleMaps` (publisher *SharpXRM Samples*, prefix `sxs`) |
| App | Google Maps Address Sample (`sxs_GoogleMapsSample`) |
| Forms | Account - Google Maps Sample, Contact - Google Maps Sample |
| Quick create forms | Account Quick Create - Google Maps Sample, Contact Quick Create - Google Maps Sample |
| Setup page | `sxs_/googlemaps/setup.html` |
| Columns | `sxs_gm_*` on Account and Contact |
| Control | `sharpxrm_GoogleMapsAddressComplete.Autocomplete` (from Address Validation for D365) |
| Flows | Verify account address with Google Maps (sample), Verify contact address with Google Maps (sample) |
| Connection reference | `sxs_googlemaps_dataverse` (Microsoft Dataverse) |

The Setup page stores your key in the API Configuration record named **SharpXrmSample_GoogleMaps**, which the sample forms use. Removing the solution does not delete that record.

## Source

[`src`](src) holds the unpacked solution (both managed and unmanaged). Rebuild the zips with `pac solution pack --zipfile SharpXrmSampleGoogleMaps.zip --folder src --packagetype Both`.
