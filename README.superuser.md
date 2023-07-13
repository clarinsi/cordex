# New Version Release Instructions

This document provides instructions for releasing a new version of the cordex library. Follow the steps below to ensure a smooth and efficient release process.

## Step 1: Update Version in `cordex/_version.py`

Open the `cordex/_version.py` file and update the version number to the desired value for the new release. This step ensures that the version number is correctly reflected in the library.

## Step 2 (Optional): Create New Lookup Lexicon

If necessary, create a new lookup lexicon by extracting data from an external database. To do this, use the `convert_lexicon_data.py` script. The script rearranges inflectional data obtained from other sources to optimize speed performance for the cordex library.

### Parameters

Ensure that the following parameters are set correctly when running the `convert_lexicon_data.py` script:

- `--sloleks_csv`: Provide the path to the CSV file containing data from external sources. The data should be saved in the format `<lemma>|<msd>|<form>|<frequency>`.
- `--output`: Specify the path to the output file that will be used by cordex.
- `--lang`: Select the language of the MSDs. Choose either "sl" for Slovenian (default) or "en" for English.

## Step 3 (Optional): Update Resources on clarin.si Repository

If applicable, upload the new version to the clarin.si repository. After the upload is complete, update the `resources.json` file in the CORDEX-RESOURCES repository with the links to the new upload on clarin.si. This step ensures that the latest resources are accessible and linked correctly.

**Note:** Insert the actual links to the clarin.si repository and CORDEX-RESOURCES repository in the respective places in the instructions.

## Step 4: Create New Release on GitHub

To provide easy access to the code in specific versions, create a new release on the GitHub repository. Use the following link to create the release: [https://github.com/clarinsi/cordex/releases/new](https://github.com/clarinsi/cordex/releases/new). Make sure to include all relevant information, such as release notes and any significant changes in the new version.

## Step 5: Upload New Version Using Twine or Other Means

Finally, upload the new version of the cordex library. You can use the twine tool (https://twine.readthedocs.io/en/stable/) or any other preferred method for uploading the package. Ensure that the uploaded version corresponds to the updated version number mentioned in Step 1.
