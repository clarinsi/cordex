""" A file containing classes related to component representation. """

import logging
from ast import literal_eval

from collections import Counter
from cordex.utils.converter import msd_to_properties
from cordex.words.word import WordDummy


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

    def add_word(self, word, is_ud):
        """ Adds word to representation. """
        self.words.append(word)

    def render(self, is_ud, lookup_lexicon=None):
        """ Render when text is not already rendered. """
        if self.rendition_text is None:
            self.rendition_text, self.rendition_msd = self._render(is_ud, lookup_lexicon=lookup_lexicon)

    # Convert output to same format as in conllu
    @staticmethod
    def convert_dict_to_string(dictionary):
        if type(dictionary) == str:
            return dictionary
        result = []
        for k, v in dictionary.items():
            result.append(f'{k}={v}')

        return '|'.join(result)

    def _render(self, is_ud, lookup_lexicon=None):
        raise NotImplementedError("Not implemented for class: {}".format(type(self)))


class LemmaCR(ComponentRepresentation):
    """ Handles lemma as component representation. """
    def _render(self, is_ud, lookup_lexicon=None):

        if len(self.words) > 0:
            lemma = self.words[0].lemma
            if is_ud:
                pos = self.convert_dict_to_string(self.words[0].udpos)
            else:
                pos = self.words[0].xpos

                if lookup_lexicon is not None:
                    msd, lemma, text = lookup_lexicon.get_word_form(lemma, pos, self.data, find_lemma_msd=True)
                    if msd is not None:
                        pos = msd
            return self.words[0].lemma, pos
        else:
            return None, None


class LexisCR(ComponentRepresentation):
    """ Handles fixed word as component representation. """
    def _render(self, is_ud, lookup_lexicon=None):
        if is_ud:
            pos = 'POS=PART'
        else:
            pos = 'Q'
        return self.data['lexis'], pos


class WordFormAllCR(ComponentRepresentation):
    """ Returns all possible word forms separated with '/' as component representation. """
    def _render(self, is_ud, lookup_lexicon=None):
        if len(self.words) == 0:
            return None, None
        else:
            forms = [w.text.lower() for w in self.words]
            if is_ud:
                msds = [self.convert_dict_to_string(w.udpos) for w in self.words]
            else:
                msds = [w.xpos for w in self.words]

            return "/".join(set(forms)), "/".join(set(msds))


class WordFormAnyCR(ComponentRepresentation):
    """ Returns any possible word form as component representation. """
    def _render(self, is_ud, lookup_lexicon=None):
        text_forms = {}
        if is_ud:
            msd_lemma_txt_triplets = Counter([(str(w.udpos), w.lemma, w.text) for w in self.words])
        else:
            msd_lemma_txt_triplets = Counter([(w.xpos, w.lemma, w.text) for w in self.words])

        for (msd, lemma, text), _n in reversed(msd_lemma_txt_triplets.most_common()):
            text_forms[(msd, lemma)] = text

        words_counter = []
        for word in self.words:
            if is_ud:
                words_counter.append((str(word.udpos), word.lemma))
            else:
                words_counter.append((word.xpos, word.lemma))
        sorted_words = sorted(
            set(words_counter), key=lambda x: -words_counter.count(x) + (sum(ord(l) for l in x[1]) / 1e5 if x[1] is not None else .5))

        # so lets got through all words, sorted by frequency
        for word_msd, word_lemma in sorted_words:
            # check if agreements match
            agreements_matched = [agr.match(word_msd, is_ud) for agr in self.agreement]

            # in case all agreements do not match try to get data from sloleks and change properly
            if lookup_lexicon is not None and not all(agreements_matched):
                for i, agr in enumerate(self.agreement):
                    if not agr.match(word_msd, is_ud):
                        msd, lemma, text = lookup_lexicon.get_word_form(agr.lemma, agr.msd(), agr.data, align_msd=word_msd)
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

                if is_ud:
                    word_msd_eval = self.convert_dict_to_string(literal_eval(word_msd))
                else:
                    word_msd_eval = word_msd
                return text_forms[(word_msd, word_lemma)], word_msd_eval
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

    def check_udpos(self, word_msd):
        """ Checks whether word msd matches the one specified in structures file. """
        if 'msd' not in self.data:
            return True
        selectors = self.data['msd']

        for key, value in selectors.items():
            if key not in word_msd or word_msd[key] != value:
                return False

        return True

    def check_xpos(self, word_msd, word_lemma):
        """ Checks whether word msd matches the one specified in structures file. """
        if 'msd' not in self.data:
            return True
        selectors = self.data['msd']

        properties = msd_to_properties(word_msd, 'en', lemma=word_lemma)
        for key, value in selectors.items():
            key_lower = key.lower()
            # if key_lower not in properties.form_feature_map and key_lower not in properties.lexeme_feature_map:
            #     return False
            if key_lower in properties and properties[key_lower] != value:
                return False

        return True

    def add_word(self, word, is_ud):
        """ Adds lemma and msd. Also adds word if word matches msd check. """
        if self.lemma is None:
            self.lemma = word.lemma

        if is_ud:
            self.msds.append(word.udpos)
            if self.check_udpos(word.udpos):
                super().add_word(word, is_ud)
        else:
            self.msds.append(word.xpos)
            if self.check_xpos(word.xpos, word.lemma):
                super().add_word(word, is_ud)

    def _render(self, is_ud, lookup_lexicon=None):
        # TODO CHECK THIS (is word dummy created twice when it should be only once?)
        if len(self.words) == 0 and lookup_lexicon is not None:
            msd, lemma, text = lookup_lexicon.get_word_form(self.lemma, self.msd(), self.data)
            if msd is not None:
                self.words.append(WordDummy(msd, lemma, text))
        if is_ud:
            self.words.append(WordDummy(self._common_udpos()))
        else:
            self.words.append(WordDummy(self._common_xpos()))
        return super()._render(is_ud, lookup_lexicon)
    
    def _common_xpos(self):
        """ Tries to form xpos that is present in all examples. """
        msds = sorted(self.msds, key=len)
        common_msd = ["-" if not all(msds[j][idx] == msds[0][idx] for j in range(1, len(self.msds))) 
                      else msds[0][idx] for idx in range(len(msds[0]))]
        common_msd = "".join(common_msd)
        return common_msd

    def _common_udpos(self):
        """ Tries to form udpos that is present in all examples. """
        udpos_key = self.msds[0]
        udpos_key_new = set(self.msds[0].keys())
        for msd in self.msds:
            for k, v in udpos_key.items():
                if k not in msd or msd[k] != v:
                    udpos_key_new.remove(k)

            udpos_key = {k: v for k, v in udpos_key.items() if k in udpos_key_new}
        return udpos_key


class WordFormAgreementCR(WordFormMsdCR):
    """ Handles word forms with agreement. """
    def __init__(self, data, word_renderer):
        super().__init__(data, word_renderer)
        self.rendition_candidate = None
        self.rendition_msd_candidate = None

    def get_agreement_head_component_id(self):
        """ Returns agreement head component id. """
        return self.data['other']

    def match(self, word_msd, is_ud):
        """ Checks if word_msd matches any of possible words in agreements. """
        if is_ud:
            existing = [(str(w.udpos), w.text) for w in self.words]
        else:
            existing = [(w.xpos, w.text) for w in self.words]

        lemma_available_words = self.word_renderer.available_words(self.lemma, existing)
        for candidate_pos, candidate_text, candidate_lemma in lemma_available_words:
            if is_ud:
                if self.msd()['POS'] != candidate_pos['POS']:
                    continue

                if WordFormAgreementCR.check_agreement_udpos(word_msd, candidate_pos, self.data['agreement']):
                    if self.check_xpos(candidate_pos, candidate_lemma):
                        self.rendition_candidate = candidate_text
                        self.rendition_msd_candidate = self.convert_dict_to_string(candidate_pos)
                        return True
            else:
                if self.msd()[0] != candidate_pos[0]:
                    continue

                if WordFormAgreementCR.check_agreement(word_msd, candidate_pos, self.data['agreement']):
                    if self.check_xpos(candidate_pos, candidate_lemma):
                        self.rendition_candidate = candidate_text
                        self.rendition_msd_candidate = candidate_pos
                        return True

        return False

    def confirm_match(self):
        """ Stores final state.  """
        self.rendition_text = self.rendition_candidate
        self.rendition_msd = self.rendition_msd_candidate

    @staticmethod
    def check_agreement_udpos(msd1, msd2, agreements):
        """ Checks if msds match in agreements. """
        msd1 = literal_eval(msd1)
        for agr_case in agreements:
            agr_case = agr_case.capitalize()

            # if not in msd, some strange msd was tries, skipping...
            if agr_case not in msd1:
                logging.warning("Cannot do agreement: {} for msd {} not found!"
                                .format(agr_case, msd1))
                return False

            if agr_case not in msd2:
                logging.warning("Cannot do agreement: {} for msd {} not found!"
                                .format(agr_case, msd2))
                return False

            # match!
            if msd1[agr_case] != msd2[agr_case]:
                return False

        return True

    @staticmethod
    def check_agreement(msd1, msd2, agreements):
        """ Checks if msds match in agreements. """
        properties1 = msd_to_properties(msd1, 'en')
        properties2 = msd_to_properties(msd2, 'en')
        for agr_case in agreements:
            # if not in msd, some strange msd was tries, skipping...
            if agr_case not in properties1:
                return False

            if agr_case not in properties2:
                return False

            p1 = properties1[agr_case]
            p2 = properties2[agr_case]

            # match!
            if p1 != p2:
                return False

        return True

    def render(self, is_ud, lookup_lexicon=None):
        pass
