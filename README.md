# Navodila

Potrebne datoteke:

* korpus v "ssj500k obliki"
* definicije struktur
* Python 3.5+

Priporocam: pypy3 paket za hitrejse poganjanje.

Primer uporabe: `python3 cordex.py ssj500k.xml Kolokacije_strukture.xml  izhod.csv`

# About

This script was developed to extract collocations from text in TEI format. Collocations are extracted and presented based on rules provided in structure file (example in `collocation-structures.xml`).

# Setup

Script may be run via python3 or pypy3. We suggest usage of virtual environments.

```bash
pip install -r requirements.txt
```


# Running

```bash
python3 cordex.py <LOCATION TO STRUCTURES> <EXTRACTION TEXT> --out <RESULTS FILE>
```

## Most important optional parameters

### --sloleks_db
This parameter is may be used, if you have access to sloleks_db. Parameter is useful when lemma_fallback would be shown in results file, because if you have sloleks_db script looks into this database to find correct replacement. 

To use this sqlalchemy has to be installed as well.

This parameter has to include information about database in following order:

<DB_USERNAME>:<DB_PASSWORD>:<DB_NAME>:<DB_URL>

### --collocation_sentence_map_dest
If value for this parameter exists (it should be string path to directory), files will be generated that include links between collocation ids and sentence ids.

### --db
This is path to file which will contain sqlite database with internal states. Used to save internal states in case code gets modified.

We suggest to put this sqlite file in RAM for faster execution. To do this follow these instructions:

```bash
sudo mkdir /mnt/tmp
sudo mount -t tmpfs tmpfs /mnt/tmp
```

If running on big corpuses (ie. Gigafida have database in RAM):
```bash
sudo mkdir /mnt/tmp
sudo mount -t tmpfs tmpfs /mnt/tmp
sudo mount -o remount,size=110G,noexec,nosuid,nodev,noatime /mnt/tmp
```

Pass path to specific file when running `cordex.py`. For example:
```bash
python3 cordex.py ... --db /mnt/tmp/mysql-cordex-ssj500k ...
```

### --multiple-output
Used when we want multiple output files (one file per structure_id).


## Instructions for running on big files (ie. Gigafida)

Suggested running with saved mysql file in tmpfs. Instructions:

```bash
sudo mkdir /mnt/tmp
sudo mount -t tmpfs tmpfs /mnt/tmp
```

If running on big corpuses (ie. Gigafida have database in RAM):
```bash
sudo mkdir /mnt/tmp
sudo mount -t tmpfs tmpfs /mnt/tmp
sudo mount -o remount,size=110G,noexec,nosuid,nodev,noatime /mnt/tmp
```