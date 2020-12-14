# Demographic explorer

Static site generator to process mySociety service data and generate demographic breakdowns. 


Live version: https://research.mysociety.org/sites/explorer/

## Setup

Set the `BUILD_PATH` (where the completed site will be rendered to, not necessary for local work) in `config.py`

You will need to run the 'explorer' and 'wttexplorer' exports from the [Export Tool](https://github.com/mysociety/fms_export) and make those avalaible on the same computer. 
If updating a previous version of the source folder, delete the contents of the `pickles` and `grid` folders inside those folders (these cache results).

The legacy WDTK Survey can be downloaded from `survey.mysociety.org` - download restricted to 'WhatDoTheyKnow' and name `reduced_survey.csv` and place in the WDTK path referenced in the config.py (this only needs this one file).

These are configured in the `config.py` as below:

```
FMS_CURRENT_YEAR = 2019
WTT_CURRENT_YEAR = 2019
WDTK_EXPLORER_SOURCE = 2019
FMS_EXPLORER_SOURCE = r"[path]\explorer"
WTT_EXPLORER_SOURCE = r"[path]\wttexplorer"
WDTK_EXPLORER_SOURCE = ""
```

With the above set up, run the following to set up a local instance:

```
pipenv install
pipenv shell
invoke migrate
invoke populate
```

To run locally use `pipenv run manage.py runserver`.

The site can then be viewed at http://127.0.0.1:8000/sites/explorer/

## Uploading

To render to the specified location use `python manage.py bake`. If not running in a vagrant, this will require a path to a CHROME_DRIVER in `config.py`.

Upload involves creating a zip and uploading via scp. Look at `tasks.py` for more details, but after setting up ssh details in `conf.ssh_creds.py` (usually reference to location of key). 

`invoke bakezip`
`invoke uploadzip`