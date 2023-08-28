"""
Corpus loaders.
"""
import os
from xml.etree import ElementTree
import logging
import re
import sys
import pathlib
from io import StringIO
import conllu
from conversion_utils.jos_msds_and_properties import Converter

from cordex.utils.converter import translate_jos_depparse
from cordex.utils.progress_bar import progress
from cordex.words.word import WordUD, WordJOS


def load_files(args, database):
    """ Loads corpora in various formats. """
    filenames = args['corpus']

    if len(filenames) == 1 and os.path.isdir(filenames[0]):
        all_filenames = []
        for path, subdirs, files in os.walk(filenames[0]):
            for name in files:
                if name[-5:] != '.zstd':
                    all_filenames.append(os.path.join(path, name))
        filenames = all_filenames

    if len(filenames) > 1:
        filenames = [filename for filename in filenames if filename[-5:] != '.zstd']
        filenames = sorted(filenames)

    database.init("CREATE TABLE Files ( filename varchar(2048) )")

    for idx, fname in enumerate(filenames):
        logging.info("FILE " + fname + "{}/{}".format(idx, len(filenames)))
        extension = pathlib.Path(fname).suffix

        # check if file with the same name already loaded...
        loaded = database.execute("SELECT * FROM Files WHERE filename=?", (fname,)).fetchone()
        if loaded is not None:
            logging.info("ALREADY LOADED")
            continue

        if extension == ".xml":
            et = load_tei(fname)
            yield tei_sentence_generator(et, args)
        elif extension == ".conllu" or extension == ".conllup":
            yield load_conllu(fname, args)
        else:
            raise Exception(f'File {fname} is in incorrect format (it should be .xml, .conllu or .conllup).')

        database.execute("INSERT INTO Files (filename) VALUES (?)", (fname,))
        database.commit()


def load_conllu(filename, args):
    """ Loads corpus file in conllu format. """
    if args['jos_msd_lang'] == 'sl':
        raise NotImplementedError('jos_msd_lang == "sl" is not implemented for conllu data!')
    result = []

    words = {}
    links = []

    def sentence_end(bad_sentence, sent_id):
        if bad_sentence:
            return

        for lfrom, ldest, ana in links:
            if lfrom not in words or ldest not in words:
                logging.warning("Bad link in sentence: " + sent_id)
                continue
            words[lfrom].add_link(ana, words[ldest])
        result.extend(words.values())

    with open(filename, 'r', encoding="UTF-8") as f:
        data = f.read()

        conlls = conllu.parse_incr(StringIO(data))
        # build dep parse
        for sent in conlls:
            try:
                if len(sent) == 0:
                    continue

                # adding fake word
                if args['is_ud']:
                    words['0'] = WordUD.fake_root_word('0')
                else:
                    words['0'] = WordJOS.fake_root_word('0')

                for word in sent:
                    if type(word['id']) == tuple:
                        continue

                    if args['is_ud']:
                        words[str(word['id'])] = WordUD.from_conllu_element(word, sent)
                        links.append((str(word['head']), str(word['id']), word['deprel']))
                    else:
                        words[str(word['id'])] = WordJOS.from_conllu_element(word, sent)
                        links.append((str(word['head']), str(word['id']), translate_jos_depparse(word['deprel'], args['jos_depparse_lang'] != 'sl')))
                if 'sent_id' in sent.metadata:
                    metadata = sent.metadata['sent_id']
                else:
                    logging.warning(f'At least one sentence is missing `sent_id`. This may lead to incomplete output in collocation_sentence_mapper.')
                    metadata = ''
                sentence_end(False, metadata)
                links = []
                words = {}
            except:
                links = []
                words = {}
                logging.error(f"Error while reading file {filename} in sentence {sent.metadata['sent_id']}. Check if required data is available!")

    return result


def load_tei(filename):
    """ Loads corpus file in TEI format. """
    with open(filename, 'r') as fp:
        content = fp.read()

    xmlstring = re.sub(' xmlns="[^"]+"', '', content, count=1)
    xmlstring = xmlstring.replace(' xml:', ' ')
    return ElementTree.XML(xmlstring)


def tei_sentence_generator(et, args):
    """ Generates sentences from TEI format. """
    do_msd_translate = not args['jos_msd_lang'] == 'en'
    do_msd_translate = Converter() if do_msd_translate else False

    words = {}
    teis = list(et.iter('{http://www.tei-c.org/ns/1.0}TEI'))

    ns = '{http://www.tei-c.org/ns/1.0}' if len(teis) != 0 else ''

    # if not TEI element search for paragraphs only
    teis = [et] if len(teis) == 0 else teis

    for tei in teis:
        paragraphs = list(tei.iter(ns + 'p'))
        for paragraph in progress(paragraphs, "load-text"):
            sentences = list(paragraph.iter(ns + 's'))
            for sentence in sentences:
                # create fake root word
                if args['is_ud']:
                    word = WordUD.fake_root_word(sentence.get('id'))
                else:
                    word = WordJOS.fake_root_word(sentence.get('id'))
                words[sentence.get('id')] = word
                previous_word = word

                for w in sentence.iter():
                    if w.tag == ns + 'w':
                        if args['is_ud']:
                            word = WordUD.from_tei_element(w, do_msd_translate)
                        else:
                            word = WordJOS.from_tei_element(w, do_msd_translate)

                        word.previous_glue = previous_word.glue
                        words[w.get('id')] = word
                        previous_word = word

                    elif w.tag == ns + 'pc':
                        if args['is_ud']:
                            word = WordUD.pc_word(w, do_msd_translate)
                        else:
                            word = WordJOS.pc_word(w, do_msd_translate)

                        word.previous_glue = previous_word.glue
                        words[w.get('id')] = word
                        previous_word = word

                for l in sentence.iter(ns + "link"):
                    if 'dep' in l.keys():
                        ana = l.get('afun')
                        lfrom = l.get('from')
                        dest = l.get('dep')
                    else:
                        ana = l.get('ana')
                        if args['is_ud']:
                            if ana[:7] != 'ud-syn:':  # dont bother...
                                continue
                            ana = ana[7:]
                            lfrom, dest = l.get('target').replace('#', '').split()
                        else:
                            if ana[:8] != 'jos-syn:':  # dont bother...
                                continue
                            ana = ana[8:]
                            lfrom, dest = l.get('target').replace('#', '').split()

                    if lfrom in words:
                        if dest in words:
                            next_word = words[dest]
                            translated_ana = translate_jos_depparse(ana, args['jos_depparse_lang'] != 'sl')
                            words[lfrom].add_link(translated_ana, next_word)
                        else:
                            logging.error("Unknown id: {}".format(dest))
                            sys.exit(1)

                    else:
                        # strange errors, just skip...
                        pass

    return list(words.values())
