import filecmp
import os
import shutil

import pytest
import cordex
from tests import *
from tests.correct_output import OUTPUT_TOKEN_OUTPUT, OUTPUT_GET_LIST


@pytest.fixture(scope="module")
def clear_output():
    """ Erases temporary files and creates new folders. """
    output_mapper_dir = os.path.join(OUTPUT_DIR, "tmp_collocation_sentence_mapper")
    if os.path.exists(output_mapper_dir):
        shutil.rmtree(output_mapper_dir)
    os.makedirs(output_mapper_dir)
    output_dir = os.path.join(OUTPUT_DIR, "izhod.csv")

    return os.path.join(output_mapper_dir, 'mapper.csv'), output_dir


def compare_directories(cor_output, output):
    for c_o, o in zip(list(os.walk(cor_output)), list(os.walk(output))):
        c_o_subdir, c_o_dirs, c_o_files = c_o
        o_subdir, o_dirs, o_files = o
        for c_o_f, o_f in zip(c_o_files, o_files):
            assert filecmp.cmp(os.path.join(c_o_subdir, c_o_f), os.path.join(o_subdir, o_f))


def test_download(clear_output):
    """ Test for cordex download. """
    cordex.download()


def test_tei_multiple_ud_documents(clear_output):
    """ Test for tei multiple documents. """
    output_mapper_dir, output_dir = clear_output

    extractor = cordex.Pipeline(os.path.join(STRUCTURES_DIR, "structures_UD.xml"),
                           collocation_sentence_map_dest=output_mapper_dir,
                           lang='en', jos_msd_lang='en')
    extraction = extractor(os.path.join(INPUT_DIR, "gigafida_example_tei_small"))
    extraction.write(output_dir, separator=',')
    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_tei_multiple_ud_documents'), os.path.join(OUTPUT_DIR))


def test_tei_single_jos_document(clear_output):
    """ Test for tei single document. """
    output_mapper_dir, output_dir = clear_output

    extractor = cordex.Pipeline(os.path.join(STRUCTURES_DIR, "structures_JOS.xml"),
                           collocation_sentence_map_dest=output_mapper_dir, jos_msd_lang='sl')
    extraction = extractor(os.path.join(INPUT_DIR, "ssj500k.small.xml"))
    extraction.write(output_dir, separator=',')
    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_tei_single_jos_document'), os.path.join(OUTPUT_DIR))


def test_tei_single_ud_document(clear_output):
    """ Test for tei single document. Also tests no statistics output"""
    output_mapper_dir, output_dir = clear_output

    extractor = cordex.Pipeline(os.path.join(STRUCTURES_DIR, "structures_UD.xml"),
                           collocation_sentence_map_dest=output_mapper_dir, statistics=False)
    extraction = extractor(os.path.join(INPUT_DIR, "ssj500k.small.xml"))
    extraction.write(output_dir, separator=',')
    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_tei_single_ud_document'), os.path.join(OUTPUT_DIR))


def test_conllu_single_jos_document(clear_output):
    """ Test for conllu single jos document. """
    output_mapper_dir, output_dir = clear_output

    extractor = cordex.Pipeline(os.path.join(STRUCTURES_DIR, "structures_JOS.xml"),
                           collocation_sentence_map_dest=output_mapper_dir, jos_depparse_lang="en")
    extraction = extractor(os.path.join(INPUT_DIR, "test_conllu_jos_small.conllu"))
    extraction.write(output_dir, separator=',')

    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_conllu_single_jos_document'), os.path.join(OUTPUT_DIR))


def test_conllu_multiple_ud_documents(clear_output):
    """ Test for conllu multiple ud documents. """
    output_mapper_dir, output_dir = clear_output

    extractor = cordex.Pipeline(os.path.join(STRUCTURES_DIR, "structures_UD.xml"),
                           collocation_sentence_map_dest=output_mapper_dir)
    extraction = extractor(os.path.join(INPUT_DIR, "gigafida_example_conllu_small"))
    extraction.write(output_dir, separator=',')

    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_conllu_multiple_ud_documents'), os.path.join(OUTPUT_DIR))


def test_conllu_single_ud_document(clear_output):
    """ Test for conllu single ud document. """
    output_mapper_dir, output_dir = clear_output

    extractor = cordex.Pipeline(os.path.join(STRUCTURES_DIR, "structures_UD.xml"),
                           collocation_sentence_map_dest=output_mapper_dir)
    extraction = extractor(os.path.join(INPUT_DIR, "ssj500k.small.conllu"))
    extraction.write(output_dir, separator=',')

    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_conllu_single_ud_document'), os.path.join(OUTPUT_DIR))


def test_get_list():
    """ Test for conllu single ud document. """
    extractor = cordex.Pipeline(os.path.join(STRUCTURES_DIR, "structures_UD.xml"))
    extraction = extractor(os.path.join(INPUT_DIR, "ssj500k.small.conllu"))
    output = extraction.get_list()

    assert OUTPUT_GET_LIST == str(output)


def test_tei_multiple_jos_documents(clear_output):
    """ Test for tei multiple documents. """
    output_mapper_dir, output_dir = clear_output

    extractor = cordex.Pipeline(os.path.join(STRUCTURES_DIR, "structures_JOS.xml"),
                           collocation_sentence_map_dest=output_mapper_dir,
                           lang='en', jos_msd_lang='sl')
    extraction = extractor(os.path.join(INPUT_DIR, "gigafida_example_tei_small"))
    extraction.write(output_dir, separator=',')
    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_tei_multiple_jos_documents'), os.path.join(OUTPUT_DIR))


def test_lookup_api(clear_output):
    """ Test for conllu single jos document. """
    output_mapper_dir, output_dir = clear_output

    extractor = cordex.Pipeline(os.path.join(STRUCTURES_DIR, "structures_JOS.xml"),
                           collocation_sentence_map_dest=output_mapper_dir, lookup_api=True, jos_depparse_lang="en")
    extraction = extractor(os.path.join(INPUT_DIR, "test_conllu_jos_small.conllu"))
    extraction.write(output_dir, separator=',')

    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_conllu_single_jos_document'), os.path.join(OUTPUT_DIR))


def test_no_lookup_jos(clear_output):
    """ Test for lookup api. """
    output_mapper_dir, output_dir = clear_output

    extractor = cordex.Pipeline(os.path.join(STRUCTURES_DIR, "structures_JOS.xml"),
                           collocation_sentence_map_dest=output_mapper_dir, lookup_lexicon=None, jos_msd_lang='sl')
    extraction = extractor(os.path.join(INPUT_DIR, "gigafida_example_tei_small"))
    extraction.write(output_dir, separator=',')
    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_no_lookup'), os.path.join(OUTPUT_DIR))
