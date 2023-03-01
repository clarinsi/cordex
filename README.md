# Instructions

Necessary files:

* corpus in conllu or TEI format
* file with structures definitions
* Python 3.5+

We suggest usage of pypy3 for faster processing.

# About

This script was developed to extract collocations from text in conllu or TEI format. Collocations are extracted and presented based on rules provided in structure file (examples in `tests/test_data/structures`).

# Setup

Script may be run via python3 or pypy3. We suggest usage of virtual environments.

```bash
pip install -r requirements.txt
```


# Running

Execution consists of three parts:
* setup
* execution
* collecting results

```python
import cordex

# setup
extractor = cordex.Pipeline("tests/test_data/structures/structures_UD.xml")
# execution
extraction = extractor("tests/test_data/input/ssj500k.small.conllu")
# collecting results
extraction.write("data/izhod.csv")
```

## Setup
During this step you should provide processing settings. There is only one required parameter - path to structures file. Other parameters are optional.

### Example

```python
extractor = cordex.Pipeline("tests/test_data/structures/structures_UD.xml", statistics=False)
```

### Parameters

#### structures
Required. Path to file with structures definitions. Examples of such file are available in `tests/test_data/structures`.

#### collocation_sentence_map_dest
Default value `None`. Optional parameter, that should contain path to file or folder, where mappings between collocations and sentences will be saved. If this is set to `None` mappings will not be stored. When the `path` in write function leads to a file all mappings will also be stored in a file. Otherwise, program will create a directory at this destination and store mappings in multiple files inside this directory, one file per one syntactic structure.

#### min_freq
Default value `0`. Number that indicate how many occurrences in corpus a collocation needs to be present in results.

#### db
Default value `None`. Path to interprocessing sqlite database file (if there is no file in that location it will create a new file). It enables us to process corpus in steps, and stores half processed data. This parameter is useful for processing bigger corpora, as a failsafe system. Value `None` indicates that data will be stored only in memory.

#### overwrite_db
Default value `False`. This parameter should be used together with parameter `db`. When `True` it will overwrite old database file and start processing from the beginning. 

#### jos_msd_lang
Default value `en`. Set this to `sl` when xpos tags are in Slovenian.

#### ignore_punctuations
Default value `False`. When this is `True`, results containing punctuations will not be shown.

#### fixed_restriction_order
Default value `False`. When this is `True`, results, where structure components are not in the same order as in structure definition files, will be ignored.

#### lookup_lexicon
Default value `None`. Path to lookup lexicon. Lexicon is used to improve representations when JOS system is used. Value `None` indicates that we are not using lookup lexicon.

#### statistics
Default value `True`. Parameter that indicates whether we want statistics in output file or not.

#### lang
Default value `sl`. Parameter that enables postprocessing for specific languages. Should contain lowercased 2-letter country abbreviation. 

#### jos_depparse_lang
Default value `en`. When using JOS system, extraction will work with Slovenian (`sl`) or English (`en`) dependency parsing tags. This is not connected to UD dependency parsing in any way. 

## Execution
During this step extraction executes.

### Example

```python
extraction = extractor("tests/test_data/input/ssj500k.small.conllu")
```

### Parameters

#### corpus
Required. Path to corpus we want to be processed. Data may be in conllu or TEI format. This path should point to either concrete file containing corpus or directory containing multiple files in the same format. Examples of such files/folders are available in `tests/test_data/input`.

## Collecting results
We support two ways of obtaining results. You may use function `write`, to write results directly. You may also use function `get_list`, which will return a list with results.

### Examples

Write example:
```python
extraction.write("data/izhod.csv")
```

Get list example:
```python
results = extraction.get_list(sort_by=1, sort_reversed=True)
```

### Parameters

#### path
Required in `write` function. Destination where results are going to be written. If this is a path to a folder, results are going to be stored in multiple files, otherwise in a single file.

#### separator
Default value `,`. Optional parameter in `write` and `get_list` functions, that tells us what output files should be separated by. For `.tbl` files shis should be `\t`.

#### sort_by
Default value `-1`. Parameter in `write` and `get_list` functions indicating by which column processing results will be sorted. Value `-1` indicates that results will be sorted by the order of structures given in structure definitions file.

#### sort_reversed
Default value `False`. This parameter is related to `sort_by`. When set to `True`, results will be sorted in reverse order of selected column.



```bash
python3 cordex.py <LOCATION TO STRUCTURES> <EXTRACTION TEXT> --out <RESULTS FILE>
```

## Instructions for running on big files (ie. Gigafida)

You should run script using pypy3.

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