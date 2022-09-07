"""
Word objects.
"""

from collections import defaultdict
import logging
from conversion_utils.jos_msds_and_properties import Msd

from corpex.readers.msd_translate import MSD_TRANSLATE


class WordDummy:
    """
    Fake word used in representation. These are used when none of the words in input satisfy checks (ie. no word with
    such msd). In these cases try to form word from inflectional lexicon.
    """
    def __init__(self, msd, lemma=None, text=None):
        self.msd = msd
        self.lemma = lemma
        self.text = text


class Word:
    """
    Base word model.
    """
    def __init__(self, lemma, msd, wid, text, do_msd_translate, fake_word=False, previous_punctuation=None):
        self.lemma = lemma

        self.msd = do_msd_translate.properties_to_msd(do_msd_translate.msd_to_properties(Msd(msd, 'sl'), 'en', lemma), 'en').code if do_msd_translate else msd
        # self.msd = do_msd_translate.translate_msd(Msd(msd, 'sl'), 'en').code if do_msd_translate else msd
        self.idi = None
        self.text = text
        self.glue = False
        self.previous_glue = False if previous_punctuation is None else previous_punctuation
        self.fake_word = fake_word

        self.links = defaultdict(list)

        split_id = wid.split('.')
        self.id = split_id[-1]
        self.sentence_id = '.'.join(split_id[:-1]) if not fake_word else wid
        last_num = split_id[-1]
        if last_num[0] not in '0123456789':
            last_num = last_num[1:]
        self.int_id = int(last_num)

        assert None not in (wid, self.lemma, self.msd)

    @staticmethod
    def from_tei_element(xml, do_msd_translate):
        """ Creates word from TEI word element. """
        lemma = xml.get('lemma')
        msd = Word.get_msd(xml)
        wid = xml.get('id')
        text = xml.text
        return Word(lemma, msd, wid, text, do_msd_translate)

    @staticmethod
    def from_conllu_element(token, sentence, do_msd_translate):
        """ Creates word from TEI word element. """
        full_id = "{}.{}".format(sentence.metadata['sent_id'], str(token['id']))
        return Word(token['lemma'], token['upos'], full_id, token['form'], False)

    @staticmethod
    def get_msd(comp):
        """ Returns word msd. """
        d = dict(comp.items())
        if 'ana' in d:
            return d['ana'][4:]
        elif 'msd' in d:
            return d['msd']
        else:
            logging.error(d)
            raise NotImplementedError("MSD?")

    @staticmethod
    def pc_word(pc, do_msd_translate):
        """ Creates punctuation from TEI punctuation element. """
        pc.set('lemma', pc.text)
        pc.set('msd', "N" if do_msd_translate else "U")
        return Word.from_tei_element(pc, do_msd_translate)

    @staticmethod
    def fake_root_word(sentence_id):
        """ Creates a fake word. """
        return Word('', '', sentence_id, '', False, True)

    def add_link(self, link, to):
        """ Adds dependency parsing link to word. """
        self.links[link].append(to)

    def get_links(self, link):
        """ Returns links of specific type. """
        if link not in self.links and "|" in link:
            for l in link.split('|'):
                self.links[link].extend(self.links[l])

        return self.links[link]