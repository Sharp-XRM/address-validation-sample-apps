# SharpXRM Address Validation sample apps

Ready-to-import sample apps for **[Address Validation for Dataverse](https://appsource.microsoft.com/product/dynamics-365/sharpxrm.dataqualitypa)** by [SharpXRM](https://www.sharpxrm.com), the address autocomplete and verification add-on for Dynamics 365 and Power Apps. Each sample shows one address provider working on Account and Contact forms (including quick create forms), so you can try a provider in a few minutes and see every value its control returns.

> These samples contain **no API keys or credentials**. You bring your own key from the provider, and the sample's Setup page stores it in your own environment.

| Sample | Provider key you need | Background verification flows | Download (managed) |
|---|---|---|---|
| [Google Maps](GoogleMaps) | Google Maps API key (Places API (New), Geocoding API and Address Validation API enabled) | Google Address Validation | [zip](dist/SharpXrmSampleGoogleMaps_1_0_0_0_managed.zip) |
| [Azure Maps](AzureMaps) | Azure Maps subscription key | Azure Maps address search | [zip](dist/SharpXrmSampleAzureMaps_1_0_0_0_managed.zip) |
| [Melissa Express Entry](MelissaExpressEntry) | Melissa licence key with Global Express Entry and Global Address Verification | Melissa Global Address Verification | [zip](dist/SharpXrmSampleMelissaExpressEntry_1_0_0_0_managed.zip) |
| [Canada Post](CanadaPost) | Canada Post AddressComplete key | None (Canada Post has no background verification) | [zip](dist/SharpXrmSampleCanadaPost_1_0_0_0_managed.zip) |
| [PostGrid](PostGrid) | PostGrid public key (`live_pk_`) for autocomplete and secret key (`live_sk_`) for the flows | PostGrid Address Verification (US/Canada and international) | [zip](dist/SharpXrmSamplePostGrid_1_0_0_0_managed.zip) |
| [Smarty](Smarty) | Smarty embedded key for autocomplete and secret key (Auth ID:Auth Token) for the flows | Smarty US and International Street Address | [zip](dist/SharpXrmSampleSmarty_1_0_0_0_managed.zip) |
| [Byteplant](Byteplant) *(preview)* | Byteplant Address Validator API key | Byteplant Address Validator | [zip](dist/SharpXrmSampleByteplant_1_0_0_0_managed.zip) |

Every managed and unmanaged solution is also attached to the [latest release](../../releases/latest). Use the **unmanaged** solution when you want to change a sample.

## Before you start

- A Dynamics 365 or Dataverse environment with **Address Validation for Dataverse** installed and licensed ([AppSource](https://appsource.microsoft.com/product/dynamics-365/sharpxrm.dataqualitypa)). A trial licence works, but it has to cover the provider you want to try.
- **Preview provider:** the Byteplant sample needs a version of Address Validation for Dataverse that includes Byteplant. Contact [SharpXRM](https://www.sharpxrm.com) for access. The Melissa Express Entry sample needs Express Entry control 0.2.0 or later.
- A **System Administrator** or **System Customizer** to import the solution, and a System Administrator or **SharpXRM - Address Validation Administrator** to run the Setup page.
- An account and an API key from the provider. Each sample's README says where to get one.

## Try a sample

1. Download the managed zip of the sample.
2. In [Power Apps](https://make.powerapps.com), select your environment, then **Solutions > Import solution**, and import the zip. Samples with background verification flows ask for a Microsoft Dataverse connection: pick or create one, and the flows are turned on.
3. Open the sample app, for example **Google Maps Address Sample**. It opens on the **Setup** page.
4. Enter your API key and select **Save and validate**. The page creates or updates the API Configuration record the sample uses, checks the key with the provider, and shows your licence status. For PostGrid and Smarty, also enter the secret key the flows need in step 2 of the page.
5. Select **New sample account** or **New sample contact**. Type a street address in **Address search** and pick a suggestion. The Setup page suggests an address to try for each provider. **Quick create account** and **Quick create contact** open the same control on the quick create forms, which **+ New** and **Create** also use in the app.
6. The standard address columns and the provider's extra outputs fill in. Save the record to keep them.
7. A few seconds after you save, the background verification flow checks the address with the provider, writes the verified address back to the standard address columns, and adds a note with everything the provider returned. Refresh the form to see it in the **Notes** section.

The controls cache their configuration in the browser. After you change the key, refresh the browser tab (F5) before you try the control again.

## What each sample contains

Every sample is one solution from the publisher **SharpXRM Samples** (prefix `sxs`):

- **A model-driven app** with a Setup page, Accounts and Contacts.
- **An Account form and a Contact form.** They show the standard Account or Contact columns, the address search control, the standard address columns it fills, and a custom column for every extra output of the provider's control (for example *Business Website* for Google Maps or *Address Type* for Canada Post).
- **An Account and a Contact quick create form** with the same address search control and columns.
- **Custom columns** named `sxs_<provider code>_<output>` on Account and Contact, so samples never collide with each other or with your own columns.
- **A Setup page** (HTML web resource) that writes the key into an API Configuration record named `SharpXrmSample_<Provider>`.
- **Two Power Automate flows** (Google Maps, Azure Maps, Melissa, PostGrid, Smarty and Byteplant), one for Account and one for Contact, plus their Microsoft Dataverse connection reference. When an address is added or changed, they call the provider's verification action through the Dataverse connector, write the verified address back to the standard address columns, and add a note with every value returned and the raw response. They only act on records whose address was picked with that sample's control, so they never touch your other records, and they skip their own updates.
- **A Notes section** on both main forms, where the flows' notes appear.

Several samples can be installed side by side. Removing a sample's solution removes its app, forms, Setup page, flows and columns. The API Configuration records it created stay (and, for Melissa, the two Field Mappings); delete them from the Address Validation settings app if you no longer need them.

## Share a sample with other users

Sample apps are visible to administrators straight away. To let other users try them:

1. Share the app with their security role (**Power Apps > Apps > ... > Share**).
2. Make sure their roles let them read Accounts and Contacts, and give them the **SharpXRM - Address Validation User** role so the control can read its configuration. Running the Setup page needs **SharpXRM - Address Validation Administrator** (or System Administrator).

## Troubleshooting

| What you see | What to do |
|---|---|
| Setup page: *Address Validation for D365 is not installed* | Install the product first, then reopen the app. |
| Setup page: licence message | Open the Address Validation settings app to start a trial or activate your licence. The licence has to cover the provider. |
| Setup page: *saved, but it could not be validated* | Check the key and the provider-specific notes on the page. For example, the key's allowed websites must include your Dynamics 365 address. |
| The form shows the address box but no suggestions | Refresh the tab (F5) so the control reloads its configuration, and check the provider's allowed websites or origins. |
| The control shows a licence message instead of the address box | The licence is missing, expired, or doesn't cover this provider. |
| No note appears after saving | Check the *Verification flows* line on the Setup page: the flows must be on and their connection set. The flows only act when the address was picked with the sample's control. Open the flow in Power Automate to see its run history. |
| A note says *Address verification failed* | The note includes the details. Usually the verification key is missing or invalid (re-run the Setup page) or the licence does not cover the provider. |

## For maintainers

The samples are generated from [`tools/providers.json`](tools/providers.json), which lists each control, its outputs, the column each output goes to, and the verification action the flows call. [`tools/flows.py`](tools/flows.py) builds the flow definitions.

```powershell
az login
cd tools
python build_sample_apps.py --env https://yourorg.crm.dynamics.com      # create or update the apps
python package_sample_apps.py --env https://yourorg.crm.dynamics.com    # add the tables to each app, export, unpack
python write_readmes.py                                                 # refresh each sample's README
```

Both scripts accept `--only GoogleMaps,Smarty` to work on some samples only. They are idempotent: forms, pages, flows and other components get stable ids, so running them again updates the samples in place. `build_sample_apps.py` turns the flows on with a Dataverse connection of the signed-in user; pass `--dataverse-connection <connection name>` to choose which one.

To add a sample for a new provider, add an entry to `providers.json` (control name, API Configuration service type, licence name, key help, and the output-to-column map), then run the three commands.

## Support

These samples are provided as-is to help you evaluate and learn the product. For product questions, licensing, or help with a provider, contact SharpXRM support at [support@sharpxrm.com](mailto:support@sharpxrm.com) or visit [www.sharpxrm.com](https://www.sharpxrm.com). Issues and suggestions about the samples themselves are welcome in this repository's [Issues](../../issues).

Provider keys are subject to each provider's own terms and billing. Address lookups made through the samples are billed to your provider account like any other lookup.

## License

The sample apps and tools in this repository are licensed under the [MIT License](LICENSE). Address Validation for Dataverse itself is a commercial product licensed separately by SharpXRM; this licence does not grant any rights to it. Dynamics 365, Dataverse and Power Apps are trademarks of Microsoft. Google Maps, Azure Maps, Melissa, Canada Post, PostGrid, Smarty and Byteplant are trademarks of their respective owners.
