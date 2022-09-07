"""
Corpus loaders.
"""
import os
from xml.etree import ElementTree
import logging
import re
import sys
import gzip
import pathlib
from io import StringIO
import conllu
from conversion_utils.jos_msds_and_properties import Converter

from corpex.utils.progress_bar import progress
from corpex.words.word import Word


def load_files(args, database):
    """ Loads corpora in various formats. """
    filenames = args['corpus']

    if len(filenames) == 1 and os.path.isdir(filenames[0]):
        filenames = [os.path.join(filenames[0], file) for file in os.listdir(filenames[0]) if file[-5:] != '.zstd']

    if len(filenames) > 1:
        filenames = [filename for filename in filenames if filename[-5:] != '.zstd']
        filenames = sorted(filenames, key=lambda x: int(x.split('.')[-1]))

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
        elif extension == ".conllu":
            yield load_conllu(fname, args)
        else:
            raise Exception(f'File {fname} is in incorrect format (it should be .xml or .conllu).')

        database.execute("INSERT INTO Files (filename) VALUES (?)", (fname,))
        database.commit()


def load_conllu(filename, args):
    """ Loads corpus file in conllu format. """
    do_msd_translate = not args['no_msd_translate']
    if args['no_msd_translate']:
        raise NotImplementedError('no_msd_translate = True is not implemented for conllu data!')
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

    with open(filename, 'r') as f:
        data = f.read()

        conlls = conllu.parse_incr(StringIO(data))
        # build dep parse
        for sent in conlls:
            try:
                # adding fake word
                words['0'] = Word.fake_root_word('0')
                for word in sent:
                    if type(word['id']) == tuple:
                        continue

                    words[str(word['id'])] = Word.from_conllu_element(word, sent, do_msd_translate)
                    links.append((str(word['head']), str(word['id']), word['deprel']))
                sentence_end(False, sent.metadata['sent_id'])
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
    do_msd_translate = not args['no_msd_translate']
    do_msd_translate = Converter() if do_msd_translate else False
    use_punctuations = not args['ignore_punctuations']
    previous_pc = False

    words = {}
    paragraphs = list(et.iter('p'))
    for paragraph in progress(paragraphs, "load-text"):
        previous_glue = False
        sentences = list(paragraph.iter('s'))
        for sentence in sentences:
            # create fake root word
            words[sentence.get('id')] = Word.fake_root_word(sentence.get('id'))
            last_word_id = None

            if args['new_tei']:
                for w in sentence.iter():
                    if w.tag == 'w':
                        words[w.get('id')] = Word.from_tei_element(w, do_msd_translate)
                        if use_punctuations:
                            previous_glue = False if 'join' in w.attrib and w.get('join') == 'right' else True
                    elif w.tag == 'pc':
                        words[w.get('id')] = Word.pc_word(w, do_msd_translate)
                        if use_punctuations:
                            words[w.get('id')].previous_glue = previous_glue
                            words[w.get('id')].glue = False if 'join' in w.attrib and w.get('join') == 'right' else True
                            previous_glue = False if 'join' in w.attrib and w.get('join') == 'right' else True
            else:
                for w in sentence.iter():
                    if w.tag == 'w':
                        words[w.get('id')] = Word.from_tei_element(w, do_msd_translate)
                        if use_punctuations:
                            previous_glue = False
                            last_word_id = None
                    elif w.tag == 'pc':
                        words[w.get('id')] = Word.pc_word(w, do_msd_translate)
                        if use_punctuations:
                            last_word_id = w.get('id')
                            words[w.get('id')].previous_glue = previous_glue
                            previous_glue = False
                    elif use_punctuations and w.tag == 'c':
                        # always save previous glue
                        # previous_glue = w.text
                        previous_glue = True
                        if last_word_id:
                            # words[last_word_id].glue += w.text
                            words[last_word_id].glue = True

            for l in sentence.iter("link"):
                if 'dep' in l.keys():
                    ana = l.get('afun')
                    lfrom = l.get('from')
                    dest = l.get('dep')
                else:
                    ana = l.get('ana')
                    if ana[:8] != 'jos-syn:': # dont bother...
                        continue
                    ana = ana[8:]
                    lfrom, dest = l.get('target').replace('#', '').split()

                if lfrom in words:
                    if dest in words:
                        next_word = words[dest]
                        words[lfrom].add_link(ana, next_word)
                    else:
                        logging.error("Unknown id: {}".format(dest))
                        sys.exit(1)

                else:
                    # strange errors, just skip...
                    pass

    return list(words.values())
