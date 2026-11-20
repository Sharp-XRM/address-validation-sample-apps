# Canada Post address autocomplete sample

A ready-to-import model-driven app that shows the **Canada Post** address autocomplete control of SharpXRM Address Validation for Dynamics 365 on Account and Contact forms, including their quick create forms.

## Install

1. Make sure **Address Validation for D365** is installed and licensed in the environment (a trial licence works).
2. Download [`SharpXrmSampleCanadaPost_1_0_0_0_managed.zip`](../dist/SharpXrmSampleCanadaPost_1_0_0_0_managed.zip) and import it from **Power Apps > Solutions > Import solution**.
3. Open the **Canada Post Address Sample** app. It opens on the **Setup** page.
4. Enter your Canada Post AddressComplete key, then select **Save and validate**.
5. Select **New sample account** or **New sample contact**, type a street address in **Address search**, and pick a suggestion. **Quick create account** and **Quick create contact** open the same control on the quick create forms (also shown by **+ New** and the **Create** button in the app).
   For example: *111 Wellington St, Ottawa*.

## Getting a key

Where to get it: https://www.canadapost-postescanada.ca/ac/

- Copy the key of your AddressComplete account. It looks like AA11-AA11-AA11-AA11.
- In the AddressComplete account, add your Dynamics 365 address to the key's allowed URLs.

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
| `fullAddress` | Full Address (`sxs_cp_fulladdress`, sample column) |
| `POBoxNumber` | PO Box Number (`sxs_cp_poboxnumber`, sample column) |
| `streetnumber` | Building Number (`sxs_cp_buildingnumber`, sample column) |
| `streetname` | Street Name (`sxs_cp_streetname`, sample column) |
| `addresstype` | Address Type (`sxs_cp_addresstype`, sample column) |
| `datalevel` | Data Level (`sxs_cp_datalevel`, sample column) |

## What the solution contains

| Component | Name |
|---|---|
| Solution | `SharpXrmSampleCanadaPost` (publisher *SharpXRM Samples*, prefix `sxs`) |
| App | Canada Post Address Sample (`sxs_CanadaPostSample`) |
| Forms | Account - Canada Post Sample, Contact - Canada Post Sample |
| Quick create forms | Account Quick Create - Canada Post Sample, Contact Quick Create - Canada Post Sample |
| Setup page | `sxs_/canadapost/setup.html` |
| Columns | `sxs_cp_*` on Account and Contact |
| Control | `sharpxrm_ExpressEntryCanadaPost.Autocomplete` (from Address Validation for D365) |

The Setup page stores your key in the API Configuration record named **SharpXrmSample_CanadaPost**, which the sample forms use. Removing the solution does not delete that record.

## Source

[`src`](src) holds the unpacked solution (both managed and unmanaged). Rebuild the zips with `pac solution pack --zipfile SharpXrmSampleCanadaPost.zip --folder src --packagetype Both`.
