"""
A file containing classes related to component representation.
There are currently 6 different ways of processing representations. The type of processing is selected based on
structures.xml file in the following way:
if rendition="lemma" --> LemmaCR
elif rendition="lexis" --> LexisCR
elif rendition="word_form" and selection="agreement" --> WordFormAgreementCR
elif rendition="word_form" and selection="msd" --> WordFormMsdCR
elif rendition="word_form" and selection="all" --> WordFormAllCR
elif rendition="word_form" --> WordFormAnyCR

Combining selections has so far been needed only for selection="agreement" and selection="msd", so this was tested,
whereas combinations with selection="all" have so far not been needed, and hence haven't been tested.
"""

import logging
from ast import literal_eval

from collections import Counter

from conversion_utils import jos_msds_and_properties

from cordex.utils.converter import msd_to_properties, default_msd_to_properties
from cordex.words.word import WordDummy


class ComponentRepresentation:
    def __init__(self, data, word_renderer):
        self.data = data
        self.word_renderer = word_renderer

        self.words = []
        self.rendition_text = None
        self.rendition_msd = None

        self.processed_api = False
        self.api_request = []
        self.agreement = []

    def get_agreement_head_component_id(self):
        """ By default, there are no agreements. """
        return []

    def add_word(self, word, is_ud):
        """ Adds word to representation. """
        self.words.append(word)

    def render(self, is_ud, lookup_lexicon=None, lookup_api=None):
        """ Render when text is not already rendered. """
        if self.rendition_text is None:
            self.rendition_text, self.rendition_msd = self._render(is_ud, lookup_lexicon=lookup_lexicon, lookup_api=lookup_api)

        if 'format' in self.data and self.data['format'] == 'lowercase':
            self.rendition_text = self.rendition_text.lower()


    # Convert output to same format as in conllu
    @staticmethod
    def convert_dict_to_string(dictionary):
        if type(dictionary) == str:
            return dictionary
        result = []
        for k, v in dictionary.items():
            result.append(f'{k}={v}')

        return '|'.join(result)

    def _render(self, is_ud, lookup_lexicon=None, lookup_api=None):
        raise NotImplementedError("Not implemented for class: {}".format(type(self)))


class LemmaCR(ComponentRepresentation):
    """ Handles lemma as component representation. """
    def _render(self, is_ud, lookup_lexicon=None, lookup_api=None):

        if len(self.words) > 0:
            lemma = self.words[0].lemma
            if is_ud:
                pos = self.convert_dict_to_string(self.words[0].udpos)
            else:
                pos = self.words[0].xpos

                if lookup_api is not None:
                    properties = default_msd_to_properties(pos, 'en', lemma=lemma)
                    if not lookup_api.executed:
                        self.processed_api = True
                        self.api_request.append({
                            'type': 'lemma',
                            'lemma': lemma,
                            'lemma_features': properties.lexeme_feature_map,
                            "category": properties.category
                        })
                    else:
                        lemma_key = f"{lemma}_{properties.category}_{'_'.join([f'{k},{v}' for k, v in properties.lexeme_feature_map.items()])}"
                        form = lookup_api.find_lemma(lemma_key)
                        if form is not None:
                            pos = form[3]

                elif lookup_lexicon is not None:
                    msd, lemma, text = lookup_lexicon.get_word_form(lemma, pos, self.data, find_lemma_msd=True)
                    if msd is not None:
                        pos = msd
            return self.words[0].lemma, pos
        else:
            return None, None


class LexisCR(ComponentRepresentation):
    """ Handles fixed word as component representation. """
    def _render(self, is_ud, lookup_lexicon=None, lookup_api=None):
        if is_ud:
            pos = 'POS=PART'
        else:
            pos = 'Q'
        return self.data['lexis'], pos


class WordFormAllCR(ComponentRepresentation):
    """ Returns all possible word forms separated with '/' as component representation. """
    def _render(self, is_ud, lookup_lexicon=None, lookup_api=None):
        if len(self.words) == 0:
            return None, None
        else:
            forms = [w.text.lower() for w in self.words]
            if is_ud:
                msds = [self.convert_dict_to_string(w.udpos) for w in self.words]
            else:
                msds = [w.xpos for w in self.words]

            # sorts unique forms by alphabet and finds corresponding msds
            representation_forms = []
            representation_msds = []
            for form in sorted(set(forms)):
                ind = forms.index(form)
                representation_forms.append(forms[ind])
                representation_msds.append(msds[ind])

            return "/".join(representation_forms), "/".join(representation_msds)


class WordFormAnyCR(ComponentRepresentation):
    """ Returns any possible word form as component representation. """
    def _render(self, is_ud, lookup_lexicon=None, lookup_api=None):
        words_counter = []
        for word in self.words:
            if is_ud:
                words_counter.append((str(word.udpos), word.lemma))
            else:
                words_counter.append((word.xpos, word.lemma))
        words_counter_ordered = sorted(list(set(words_counter)),
                                 key=lambda x: (True, x[0], x[1]) if x[1] is not None else (False, '_', '_'))
        sorted_words = sorted(
            words_counter_ordered, key=lambda x: -words_counter.count(x) + (sum(ord(l) for l in x[1]) / 1e5 if x[1] is not None else .5))

        # so lets get through all words, sorted by frequency
        for word_msd, word_lemma in sorted_words:
            # check if agreements match
            agreements_matched = [agr.match(word_msd, is_ud) for agr in self.agreement]

            # if lookup_api exists create queries for it
            if lookup_api is not None:
                self.processed_api = True

                for i, agr in enumerate(self.agreement):
                    if not agr.match(word_msd, is_ud) or not lookup_api.executed:
                        properties = default_msd_to_properties(agr.msd(), 'en', agr.lemma)

                        # get agreement feature properties
                        agreement_properties = default_msd_to_properties(word_msd, 'en', word_lemma)
                        if 'msd' in agr.data:
                            form_features = agr.data['msd']
                        else:
                            form_features = {}

                        missing_form_features = False
                        for agreement_name in agr.data['agreement']:
                            if agreement_name in agreement_properties.form_feature_map:
                                form_features[agreement_name] = agreement_properties.form_feature_map[agreement_name]
                            elif agreement_name in agreement_properties.lexeme_feature_map:
                                form_features[agreement_name] = agreement_properties.lexeme_feature_map[agreement_name]

                            if agreement_name not in agreement_properties.form_feature_map and agreement_name not in agreement_properties.lexeme_feature_map:
                                missing_form_features = True
                                break

                        if missing_form_features:
                            continue

                        if not lookup_api.executed:
                            self.api_request.append({
                                'type': 'agreement',
                                'lemma': agr.lemma,
                                'lemma_features': properties.lexeme_feature_map,
                                'form_features': form_features,
                                "category": properties.category
                            })
                        else:
                            lemma_key = f"{agr.lemma}_{properties.category}_{'_'.join([f'{k},{v}' for k, v in properties.lexeme_feature_map.items()])}"

                            form = lookup_api.find_form(lemma_key, form_features)

                            if form is not None:
                                text = form[0]
                                msd = form[3]
                                agr.msds[0] = msd
                                agr.words.append(WordDummy(msd, agr.lemma, text))
                                # when we find element in sloleks automatically add it (no need for second checks, since msd
                                # is tailored to pass tests by default)
                                agr.rendition_candidate = text
                                agr.rendition_msd_candidate = msd
                                agreements_matched[i] = True
                            else:
                                break

            # in case all agreements do not match try to get data from sloleks and change properly
            elif lookup_lexicon is not None and not all(agreements_matched):
                for i, agr in enumerate(self.agreement):
                    if not agr.match(word_msd, is_ud):
                        msd, lemma, text = lookup_lexicon.get_word_form(agr.lemma, agr.msd(), agr.data, align_msd=word_msd, align_lemma=word_lemma)
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

                text = self.word_renderer.render(word_lemma, word_msd)

                if text:
                    return self.word_renderer.render(word_lemma, word_msd), word_msd_eval
                else:
                    if len(self.words) != 1:
                        raise ValueError('Internal database is not setup correctly! All msd - lemma combinations should be in UniqWords table. In this situation they are not.')
                    else:
                        return self.words[0].text, word_msd_eval
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

    def _render(self, is_ud, lookup_lexicon=None, lookup_api=None):
        if is_ud:
            self.words.append(WordDummy(self._common_udpos()))
        else:
            word_appended = False
            if len(self.words) == 0 and lookup_api is not None:
                properties = default_msd_to_properties(self.msd(), 'en', self.lemma)
                if not lookup_api.executed:
                    self.api_request.append({
                        'type': 'msd',
                        'lemma': self.lemma,
                        'lemma_features': properties.lexeme_feature_map,
                        'form_features': self.data['msd'],
                        "category": properties.category
                    })
                    self.processed_api = True
                    self.words.append(WordDummy(self.msd(), self.lemma, ''))
                    word_appended = True
                else:
                    lemma_key = f"{self.lemma}_{properties.category}_{'_'.join([f'{k},{v}' for k, v in properties.lexeme_feature_map.items()])}"
                    lemma = self.lemma
                    form = lookup_api.find_form(lemma_key, self.data['msd'])
                    if form is not None:
                        text = form[0]
                        msd = form[3]
                        self.words.append(WordDummy(msd, lemma, text))
                        word_appended = True

            elif len(self.words) == 0 and lookup_lexicon is not None:
                msd, lemma, text = lookup_lexicon.get_word_form(self.lemma, self.msd(), self.data)
                if msd is not None:
                    self.words.append(WordDummy(msd, lemma, text))
                    word_appended = True
            if not word_appended:
                self.words.append(WordDummy(self._common_xpos()))
        return super()._render(is_ud, lookup_lexicon, lookup_api)
    
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
        lemma_available_words = self.word_renderer.available_words(self.lemma)
        for candidate_pos, candidate_text, candidate_lemma in lemma_available_words:
            if is_ud:
                if self.msd()['POS'] != candidate_pos['POS']:
                    continue

                if WordFormAgreementCR.check_agreement_udpos(word_msd, candidate_pos, self.data['agreement']):
                    if self.check_udpos(candidate_pos):
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
        if 'format' in self.data and self.data['format'] == 'lowercase':
            self.rendition_text = self.rendition_text.lower()
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

    def render(self, is_ud, lookup_lexicon=None, lookup_api=None):
        pass
