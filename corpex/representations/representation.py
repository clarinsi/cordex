""" A file containing classes related to component representation. """

import logging

from collections import Counter
from corpex.utils.codes_tagset import TAGSET, CODES
from corpex.words.word import WordDummy


class ComponentRepresentation:
    def __init__(self, data, word_renderer):
        self.data = data
        self.word_renderer = word_renderer

        self.words = []
        self.rendition_text = None
        self.rendition_msd = None
        self.agreement = []

    def get_agreement_head_component_id(self):
        """ By default, there are no agreements. """
        return []

    def add_word(self, word, system_type):
        """ Adds word to representation. """
        self.words.append(word)

    def render(self, system_type, sloleks_db=None):
        """ Render when text is not already rendered. """
        if self.rendition_text is None:
            self.rendition_text, self.rendition_msd = self._render(system_type, sloleks_db=sloleks_db)

    def _render(self, system_type, sloleks_db=None):
        raise NotImplementedError("Not implemented for class: {}".format(type(self)))

class LemmaCR(ComponentRepresentation):
    """ Handles lemma as component representation. """
    def _render(self, system_type, sloleks_db=None):
        # TODO FIX THIS TO LEMMA MSD
        if len(self.words) > 0:
            if system_type == 'UD':
                pos = self.words[0].udpos
            else:
                pos = self.words[0].xpos
            return self.words[0].lemma, pos
        else:
            return None, None

class LexisCR(ComponentRepresentation):
    """ Handles fixed word as component representation. """
    def _render(self, system_type, sloleks_db=None):
        return self.data['lexis'], 'Q'

class WordFormAllCR(ComponentRepresentation):
    """ Returns all possible word forms separated with '/' as component representation. """
    def _render(self, system_type, sloleks_db=None):
        if len(self.words) == 0:
            return None, None
        else:
            forms = [w.text.lower() for w in self.words]
            if system_type == 'UD':
                raise NotImplementedError
            else:
                msds = [w.xpos for w in self.words]

            return "/".join(set(forms)), "/".join(set(msds))

class WordFormAnyCR(ComponentRepresentation):
    """ Returns any possible word form as component representation. """
    def _render(self, system_type, sloleks_db=None):
        text_forms = {}
        if system_type == 'UD':
            raise NotImplementedError
        else:
            msd_lemma_txt_triplets = Counter([(w.xpos, w.lemma, w.text) for w in self.words])

        for (msd, lemma, text), _n in reversed(msd_lemma_txt_triplets.most_common()):
            text_forms[(msd, lemma)] = text

        words_counter = []
        for word in self.words:
            if system_type == 'UD':
                raise NotImplementedError
            else:
                words_counter.append((word.xpos, word.lemma))
        sorted_words = sorted(
            set(words_counter), key=lambda x: -words_counter.count(x) + (sum(ord(l) for l in x[1]) / 1e5 if x[1] is not None else .5))

        # so lets got through all words, sorted by frequency
        for word_msd, word_lemma in sorted_words:
            # check if agreements match
            agreements_matched = [agr.match(word_msd, system_type) for agr in self.agreement]

            # in case all agreements do not match try to get data from sloleks and change properly
            if sloleks_db is not None and not all(agreements_matched):
                for i, agr in enumerate(self.agreement):
                    if not agr.match(word_msd, system_type):
                        msd, lemma, text = sloleks_db.get_word_form(agr.lemma, agr.msd(), agr.data, align_msd=word_msd)
                        if msd is not None:
                            agr.msds[0] = msd
                            agr.words.append(WordDummy(msd, lemma, text))
                            # when we find element in sloleks automatically add it (no need for second checks, since msd
                            # is tailored to pass tests by default)
                            agr.rendition_candidate = text
                            agr.rendition_msd_candidate = msd
                            agreements_matched[i] = True
                        else:
                            break


            # if we are at the last "backup word", then confirm matches 
            # that worked for this one and return
            if word_lemma is None:
                for agr, matched in zip(self.agreement, agreements_matched):
                    if matched:
                        agr.confirm_match()
                return None, None

            # if all agreements match, we win!
            if all(agreements_matched):
                for agr in self.agreement:
                    agr.confirm_match()

                return text_forms[(word_msd, word_lemma)], word_msd
        return None, None


class WordFormMsdCR(WordFormAnyCR):
    """ Handles component representations with msd requirement. If none of the words in input satisfy checks (ie. no
    word with such msd), try to form word from database lookups. """
    def __init__(self, *args):
        super().__init__(*args)
        self.lemma = None
        self.msds = []
    
    def msd(self):
        return self.msds[0]

    def check_msd(self, word_msd):
        """ Checks whether word msd matches the one specified in structures file. """
        if 'msd' not in self.data:
            return True
        selectors = self.data['msd']

        for key, value in selectors.items():
            t = word_msd[0]
            v = TAGSET[t].index(key.lower())
            if v + 1 >= len(word_msd):
                return False
            f1 = word_msd[v + 1]
            f2 = CODES[value]

            if '-' not in [f1, f2] and f1 != f2:
                return False

        return True

    def add_word(self, word, system_type):
        """ Adds lemma and msd. Also adds word if word matches msd check. """
        if self.lemma is None:
            self.lemma = word.lemma

        if system_type == 'UD':
            raise NotImplementedError
        else:
            self.msds.append(word.xpos)
            if self.check_msd(word.xpos):
                super().add_word(word, system_type)

    def _render(self, system_type, sloleks_db=None):
        if len(self.words) == 0 and sloleks_db is not None:
            msd, lemma, text = sloleks_db.get_word_form(self.lemma, self.msd(), self.data)
            if msd is not None:
                self.words.append(WordDummy(msd, lemma, text))
        self.words.append(WordDummy(self._common_msd()))
        return super()._render(system_type, sloleks_db)
    
    def _common_msd(self):
        msds = sorted(self.msds, key=len)
        common_msd = ["-" if not all(msds[j][idx] == msds[0][idx] for j in range(1, len(self.msds))) 
                      else msds[0][idx] for idx in range(len(msds[0]))]
        common_msd = "".join(common_msd)
        return common_msd
    

class WordFormAgreementCR(WordFormMsdCR):
    """ Handles word forms with agreement. """
    def __init__(self, data, word_renderer):
        super().__init__(data, word_renderer)
        self.rendition_candidate = None
        self.rendition_msd_candidate = None

    def get_agreement_head_component_id(self):
        """ Returns agreement head component id. """
        return self.data['other']

    def match(self, word_msd, system_type):
        """ Checks if word_msd matches any of possible words in agreements. """
        if system_type == 'UD':
            existing = [(w.xpos, w.text) for w in self.words]
        else:
            existing = [(str(w.udpos), w.text) for w in self.words]
        #existing = [(w.xpos, str(w.udpos), w.text) for w in self.words]

        lemma_available_words = self.word_renderer.available_words(self.lemma, existing, system_type)
        for candidate_pos, candidate_text in lemma_available_words:
            if system_type == 'UD':
                raise NotImplementedError
            if self.msd()[0] != candidate_pos[0]:
                continue

            if WordFormAgreementCR.check_agreement(word_msd, candidate_pos, self.data['agreement']):
                if self.check_msd(candidate_pos):
                    self.rendition_candidate = candidate_text
                    self.rendition_msd_candidate = candidate_pos
                    return True

        return False

    def confirm_match(self):
        """ Stores final state.  """
        self.rendition_text = self.rendition_candidate
        self.rendition_msd = self.rendition_msd_candidate

    @staticmethod
    def check_agreement(msd1, msd2, agreements):
        """ Checks if msds match in agreements. """
        for agr_case in agreements:
            t1 = msd1[0]
            # if not in msd, some strange msd was tries, skipping...
            if agr_case not in TAGSET[t1]:
                logging.warning("Cannot do agreement: {} for msd {} not found!"
                                .format(agr_case, msd1))
                return False

            v1 = TAGSET[t1].index(agr_case)
            # if none specified: nedolocnik, always agrees
            if v1 + 1 >= len(msd1):
                continue
            # first is uppercase, not in TAGSET
            m1 = msd1[v1 + 1]

            # REPEAT (not DRY!)
            t2 = msd2[0]
            if agr_case not in TAGSET[t2]:
                logging.warning("Cannot do agreement: {} for msd {} not found!"
                                .format(agr_case, msd2))
                return False
            v2 = TAGSET[t2].index(agr_case)
            if v2 + 1 >= len(msd2):
                continue
            m2 = msd2[v2 + 1]

            # match!
            if '-' not in [m1, m2] and m1 != m2:
                return False

        return True

    def render(self, system_type, sloleks_db=None):
        pass
