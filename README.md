# COBRAdb

COBRAdb loads genome-scale metabolic models and genome annotations into a
relational database. It already powers [BiGG Models](http://bigg.ucsd.edu), and
it is available under the MIT license.

## Installation

COBRAdb requires PostgreSQL, Python 2.7 or 3.6+, and a number of Python packages
listed in `setup.py`.

1. Install and set up PostgreSQL. This process varies from platform to platform,
   but the best place to start in the PostgreSQL
   [documentation](https://www.postgresql.org/docs/).

2. Set up your configuration. Copy the file `settings.ini.example` and rename it
   `settings.ini`. The example file includes descriptions of each setting. You
   can use the settings file from BiGG Models as a guide:
   https://github.com/SBRG/bigg_models_data

3. Install COBRAdb and dependencies.

```
python setup.py install
# OR
python setup.py develop
# OR
pip install -e .
```

4. Load the database by calling the script `bin/load_db`.

```
bin/load_db --drop-all
```
