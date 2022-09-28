"""
Word objects.
"""

from collections import defaultdict
import logging
from conversion_utils.jos_msds_and_properties import Msd

from corpex.utils.converter import translate_msd


class WordDummy:
    """
    Fake word used in representation. These are used when none of the words in input satisfy checks (ie. no word with
    such msd). In these cases try to form word from inflectional lexicon.
    """
    def __init__(self, pos, lemma=None, text=None):
        self.xpos = pos
        self.udpos = pos
        self.lemma = lemma
        self.text = text


class Word:
    """
    Base word model.
    """
    def __init__(self, lemma, upos, xpos, wid, text, do_msd_translate, fake_word=False, previous_punctuation=None, feats=None):
        self.lemma = lemma

        self.xpos = translate_msd(xpos, 'sl', lemma=lemma) if do_msd_translate else xpos
        # udpos contains both upos and feats
        if feats:
            if upos:
                feats['POS'] = upos
                udpos = feats
            else:
                # goes here when POS already in feats
                udpos = feats

        else:
            if upos:
                udpos = {'POS': upos}
            else:
                udpos = ''

        self.udpos = udpos
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

        assert None not in (wid, self.lemma, self.xpos, self.udpos)

    @staticmethod
    def from_tei_element(xml, do_msd_translate):
        """ Creates word from TEI word element. """
        lemma = xml.get('lemma')
        xpos, upos, feats = Word.get_msd(xml)
        wid = xml.get('id')
        text = xml.text
        return Word(lemma, upos, xpos, wid, text, do_msd_translate, feats=feats)

    @staticmethod
    def from_conllu_element(token, sentence):
        """ Creates word from TEI word element. """
        full_id = "{}.{}".format(sentence.metadata['sent_id'], str(token['id']))
        return Word(token['lemma'], token['upos'], token['xpos'], full_id, token['form'], False, feats=token['feats'])

    @staticmethod
    def get_msd(comp):
        """ Returns word msd. """
        d = dict(comp.items())
        assert 'ana' in d, 'Tag "ana" is not in element.'
        xpos = d['ana'][4:]

        assert 'msd' in d, 'Tag "msd" is not in element.'
        feats_expanded = {attrib.split('=')[0]: attrib.split('=')[1] for attrib in d['msd'].split('|')}
        if 'UPosTag' in feats_expanded:
            upos = feats_expanded['UPosTag']
            del feats_expanded['UPosTag']
        else:
            upos = feats_expanded['UposTag']
            del feats_expanded['UposTag']
        feats = feats_expanded
        return xpos, upos, feats

    @staticmethod
    def pc_word(pc, do_msd_translate):
        """ Creates punctuation from TEI punctuation element. """
        pc.set('lemma', pc.text)
        # TODO LOOK INTO POSSIBLE ERRORS DUE TO THIS
        # pc.set('msd', "N" if do_msd_translate else "U")
        return Word.from_tei_element(pc, do_msd_translate)

    @staticmethod
    def fake_root_word(sentence_id):
        """ Creates a fake word. """
        return Word('', '', '', sentence_id, '', False, True)

    def add_link(self, link, to):
        """ Adds dependency parsing link to word. """
        self.links[link].append(to)

    def get_links(self, link):
        """ Returns links of specific type. """
        if link not in self.links and "|" in link:
            for l in link.split('|'):
                self.links[link].extend(self.links[l])

        return self.links[link]