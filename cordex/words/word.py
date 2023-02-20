"""
Word objects.
"""

from collections import defaultdict

from cordex.utils.converter import translate_msd


def prepare_ids(wid, fake_word):
    """ Gets sentence_id, word_id and int_word_id from a string id. """
    split_id = wid.split('.')
    word_id = split_id[-1]
    sentence_id = '.'.join(split_id[:-1]) if not fake_word else wid
    last_num = split_id[-1]
    if last_num[0] not in '0123456789':
        last_num = last_num[1:]
    int_word_id = int(last_num)
    return sentence_id, word_id, int_word_id


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
    def __init__(self, lemma, sentence_id, word_id, int_word_id, text, glue, fake_word=False):
        self.lemma = lemma

        self.idi = None
        self.text = text
        self.glue = glue
        self.previous_glue = False
        self.fake_word = fake_word

        self.links = defaultdict(list)

        self.id = word_id
        self.sentence_id = sentence_id
        self.int_id = int_word_id

    @staticmethod
    def from_tei_element(xml, do_msd_translate):
        """ Creates word from TEI word element. """
        raise NotImplementedError

    @staticmethod
    def from_conllu_element(token, sentence):
        """ Creates word from TEI word element. """
        raise NotImplementedError

    @staticmethod
    def get_msd(comp):
        """ Returns word msd. """
        raise NotImplementedError

    @staticmethod
    def pc_word(pc, do_msd_translate):
        """ Creates punctuation from TEI punctuation element. """
        raise NotImplementedError

    @staticmethod
    def fake_root_word(sentence_id):
        """ Creates a fake word. """
        raise NotImplementedError

    def add_link(self, link, to):
        """ Adds dependency parsing link to word. """
        self.links[link].append(to)

    def get_links(self, link):
        """ Returns links of specific type. """
        if link not in self.links and "|" in link:
            for l in link.split('|'):
                self.links[link].extend(self.links[l])

        return self.links[link]


class WordJOS(Word):
    def __init__(self, lemma, xpos, sentence_id, word_id, int_word_id, text, glue, do_msd_translate, fake_word=False):
        self.xpos = translate_msd(xpos, 'sl', lemma=lemma) if do_msd_translate else xpos

        super().__init__(lemma, sentence_id, word_id, int_word_id, text, glue, fake_word)

    @staticmethod
    def from_tei_element(xml, do_msd_translate):
        """ Creates word from TEI word element. """
        lemma = xml.get('lemma')
        xpos = WordJOS.get_msd(xml)
        wid = xml.get('id')
        text = xml.text
        glue = 'join' in xml.attrib and xml.get('join') == 'right'
        sentence_id, word_id, int_word_id = prepare_ids(wid, False)
        return WordJOS(lemma, xpos, sentence_id, word_id, int_word_id, text, glue, do_msd_translate)

    @staticmethod
    def from_conllu_element(token, sentence):
        """ Creates word from TEI word element. """
        glue = token['misc'] is not None and 'SpaceAfter' in token['misc'] and token['misc']['SpaceAfter'] == 'No'
        metadata = sentence.metadata['sent_id'] if 'sent_id' in sentence.metadata else ''
        return WordJOS(token['lemma'], token['xpos'], metadata, str(token['id']), int(token['id']), token['form'], glue, False)

    @staticmethod
    def get_msd(comp):
        """ Returns word msd. """
        d = dict(comp.items())
        assert 'ana' in d, 'Tag "ana" is not in element.'
        xpos = d['ana'][4:]

        return xpos

    @staticmethod
    def pc_word(pc, do_msd_translate):
        """ Creates punctuation from TEI punctuation element. """
        pc.set('lemma', pc.text)
        return WordJOS.from_tei_element(pc, do_msd_translate)

    @staticmethod
    def fake_root_word(sentence_id):
        """ Creates a fake word. """
        sentence_id, word_id, int_word_id = prepare_ids(sentence_id, True)
        return WordJOS('', '', sentence_id, word_id, int_word_id, '', False, False, True)


class WordUD(Word):
    def __init__(self, lemma, upos, sentence_id, word_id, int_word_id, text, glue, fake_word=False, feats=None):
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

        super().__init__(lemma, sentence_id, word_id, int_word_id, text, glue, fake_word)

    @staticmethod
    def from_tei_element(xml, do_msd_translate):
        """ Creates word from TEI word element. """
        lemma = xml.get('lemma')
        upos, feats = WordUD.get_msd(xml)
        wid = xml.get('id')
        text = xml.text
        glue = 'join' in xml.attrib and xml.get('join') == 'right'
        sentence_id, word_id, int_word_id = prepare_ids(wid, False)
        return WordUD(lemma, upos, sentence_id, word_id, int_word_id, text, glue, feats=feats)

    @staticmethod
    def from_conllu_element(token, sentence):
        glue = token['misc'] is not None and 'SpaceAfter' in token['misc'] and token['misc']['SpaceAfter'] == 'No'
        """ Creates word from TEI word element. """
        return WordUD(token['lemma'], token['upos'], sentence.metadata['sent_id'], str(token['id']), int(token['id']), token['form'], glue, feats=token['feats'])

    @staticmethod
    def get_msd(comp):
        """ Returns word msd. """
        d = dict(comp.items())
        assert 'msd' in d, 'Tag "msd" is not in element.'
        feats_expanded = {attrib.split('=')[0]: attrib.split('=')[1] for attrib in d['msd'].split('|')}
        if 'UPosTag' in feats_expanded:
            upos = feats_expanded['UPosTag']
            del feats_expanded['UPosTag']
        else:
            upos = feats_expanded['UposTag']
            del feats_expanded['UposTag']
        feats = feats_expanded
        return upos, feats

    @staticmethod
    def pc_word(pc, do_msd_translate):
        """ Creates punctuation from TEI punctuation element. """
        pc.set('lemma', pc.text)
        return WordUD.from_tei_element(pc, do_msd_translate)

    @staticmethod
    def fake_root_word(sentence_id):
        """ Creates a fake word. """
        sentence_id, word_id, int_word_id = prepare_ids(sentence_id, True)
        return WordUD('', '', sentence_id, word_id, int_word_id, '', False, True)
