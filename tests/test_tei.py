import filecmp
import os
import shutil

import pytest
import corpex
from tests import *

@pytest.fixture(scope="module")
def clear_output():
    """ Erases temporary files and creates new folders. """
    output_mapper_dir = os.path.join(OUTPUT_DIR, "tmp_collocation_sentence_mapper")
    if os.path.exists(output_mapper_dir):
        shutil.rmtree(output_mapper_dir)
    os.makedirs(output_mapper_dir)
    output_dir = os.path.join(OUTPUT_DIR, "izhod.csv")

    return output_mapper_dir, output_dir


def compare_directories(cor_output, output):
    for c_o, o in zip(list(os.walk(cor_output)), list(os.walk(output))):
        c_o_subdir, c_o_dirs, c_o_files = c_o
        o_subdir, o_dirs, o_files = o
        for c_o_f, o_f in zip(c_o_files, o_files):
            assert filecmp.cmp(os.path.join(c_o_subdir, c_o_f), os.path.join(o_subdir, o_f))


def test_tei_multiple_documents(clear_output):
    """ Test for tei multiple documents. """
    output_mapper_dir, output_dir = clear_output

    extr = corpex.Pipeline(os.path.join(STRUCTURES_DIR, "structures.xml"),
                           collocation_sentence_map_dest=output_mapper_dir, separator=',', ignore_punctuations=True,
                           lang='en', no_msd_translate=True)
    extr(os.path.join(INPUT_DIR, "gigafida_example_tei_small"), output_dir)
    raise NotImplementedError
    # assert filecmp.cmp('file1.txt', 'file1.txt')


def test_tei_single_document(clear_output):
    """ Test for tei single document. """
    output_mapper_dir, output_dir = clear_output

    extr = corpex.Pipeline(os.path.join(STRUCTURES_DIR, "structures.xml"),
                           collocation_sentence_map_dest=output_mapper_dir, separator=',', ignore_punctuations=True)
    extr(os.path.join(INPUT_DIR, "ssj500k.small.xml"), output_dir)

    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_tei_single_document'), os.path.join(OUTPUT_DIR))


def test_conllu_single_jos_document(clear_output):
    """ Test for conllu single jos document. """
    output_mapper_dir, output_dir = clear_output

    extr = corpex.Pipeline(os.path.join(STRUCTURES_DIR, "structures.xml"),
                           collocation_sentence_map_dest=output_mapper_dir, separator=',',
                           ignore_punctuations=True)
    extr(os.path.join(INPUT_DIR, "test_conllu_jos_small.conllu"), output_dir)

    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_conllu_single_jos_document'), os.path.join(OUTPUT_DIR))


def test_conllu_multiple_ud_documents(clear_output):
    """ Test for conllu multiple ud documents. """
    output_mapper_dir, output_dir = clear_output

    extr = corpex.Pipeline(os.path.join(STRUCTURES_DIR, "Kolokacije_strukture_UD-1.1_2.xml"),
                           collocation_sentence_map_dest=output_mapper_dir, separator=',',
                           ignore_punctuations=True)
    extr(os.path.join(INPUT_DIR, "gigafida_example_conllu_small"), output_dir)

    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_conllu_multiple_ud_documents'), os.path.join(OUTPUT_DIR))


def test_conllu_single_ud_document(clear_output):
    """ Test for conllu single ud document. """
    output_mapper_dir, output_dir = clear_output

    extr = corpex.Pipeline(os.path.join(STRUCTURES_DIR, "Kolokacije_strukture_UD-1.1_2.xml"),
                           collocation_sentence_map_dest=output_mapper_dir, separator=',',
                           ignore_punctuations=True)
    extr(os.path.join(INPUT_DIR, "ssj500k.small.conllu"), output_dir)

    compare_directories(os.path.join(CORRECT_OUTPUT_DIR, 'output_conllu_single_ud_document'), os.path.join(OUTPUT_DIR))

    # assert filecmp.cmp(os.path.join(CORRECT_OUTPUT_DIR, 'output_conllu_single_ud_document', 'izhod.csv'), os.path.join(OUTPUT_DIR, 'izhod.csv'))




# # TEI
# # extr = corpex.Pipeline("data/structures/structures_ADAPTED2.xml", out="data/izhod.csv", collocation_sentence_map_dest="data/collocation_sentence_mapper", separator=',', ignore_punctuations=True, sloleks_db='luka:akul:superdb_small:127.0.0.1')
#
# extr = corpex.Pipeline("data/structures/Kolokacije_strukture_UD-1.1_2.xml", out="data/izhod.csv", collocation_sentence_map_dest="data/collocation_sentence_mapper", separator=',', ignore_punctuations=True, sloleks_db='luka:akul:superdb_small:127.0.0.1', lang='en', no_msd_translate=True)
# # extr("data/input/ssj500k-sl.body.small.xml", "data/izhod.csv")
# extr("data/input/gigafida_example_tei_small", "data/izhod.csv")
# # extr("data/input/ssj500k.minimal.bug.xml", "data/izhod.csv")
# # extr("data/input/ssj500k.xml", "data/izhod.csv")
#
# ##############################################
#
# # CONLLU
# # JOS
# extr = corpex.Pipeline("data/structures/structures.xml", out="data/izhod.csv", collocation_sentence_map_dest="data/collocation_sentence_mapper", separator=',', ignore_punctuations=True, sloleks_db='luka:akul:superdb_small:127.0.0.1')
# extr("data/input/test_conllu_jos_small.conllu", "data/izhod.csv")


# UD
# extr = corpex.Pipeline("data/structures/Kolokacije_strukture_UD-1.1_2.xml", out="data/izhod.csv", collocation_sentence_map_dest="data/collocation_sentence_mapper", separator=',', ignore_punctuations=True, sloleks_db='luka:akul:superdb_small:127.0.0.1')
# # extr = corpex.Pipeline("data/structures/Kolokacije_strukture_UD-1.1_2_ADAPTED.xml", out="data/izhod.csv", collocation_sentence_map_dest="data/collocation_sentence_mapper", separator=',', ignore_punctuations=True, sloleks_db='luka:akul:superdb_small:127.0.0.1')
# # extr("data/input/ssj500k.small.conllu", "data/izhod.csv")
# # extr("data/input/ssj500k.conllu", "data/izhod.csv")
# extr("data/input/gigafida_example_conllu_small", "data/izhod.csv")
# # extr("data/input/ssj500k.minimal.conllu", "data/izhod.csv")
