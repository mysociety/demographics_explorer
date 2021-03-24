# Demographic explorer

Static site generator to process mySociety service data and generate demographic breakdowns. 


Live version: https://research.mysociety.org/sites/explorer/

## Setup

Set the `BUILD_PATH` (where the completed site will be rendered to, not necessary for local work) in `config.py`

You will need to run the 'explorer' and 'wttexplorer' exports from the [Export Tool](https://github.com/mysociety/fms_export) and make those avalaible on the same computer. 
If updating a previous version of the source folder, delete the contents of the `pickles` and `grid` folders inside those folders (these cache results).

The legacy WDTK Survey can be downloaded from `https://secure.mysociety.org/admin/survey/` - download restricted to 'WhatDoTheyKnow' and name `reduced_survey.csv` and place in the WDTK path referenced in the config.py (this only needs this one file).

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

## Deployment

The deploy process uses docker to build a directory of static images that should then be deployed to a server. The instructions for doing this on mySociety infrastructure are:

* Clone this repository / `git pull origin` if updating an existing folder.
* `script/bootstrap` will create an `.env` file from the `.env-example` file if not present. Update this using secret settings from `research minisites` page of the wiki. 
* Run `script/build` to create the docker image and populate the database.
* Run `script/bake` to create the static files in the `bake_dir` directory. This creates a detached docker process that can be reattached with `script/attach` or monitored with `script/logs --follow` (which is run automatically but can be exited).
* With correctly configured `.env` file, run `script/publish` to copy the static files to a tarball, copy it to the deployment server, and untar in the appropriate location (requires sudo password).