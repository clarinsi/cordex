"""
Classes for handling restrictions.
"""
import re
from enum import Enum

from corpex.utils.codes_tagset import CODES, TAGSET, CODES_UD
from corpex.utils.converter import msd_to_properties


class RestrictionType(Enum):
    Morphology = 0
    Lexis = 1
    MatchAll = 2
    Space = 3
    MorphologyUD = 4


def determine_ppb_ud(rgxs):
    """ Determine if a word has full meaning - UD (returns priority). """
    if len(rgxs) != 1:
        return 0
    rgx = rgxs[0]
    if rgx in ("ADJ", "NOUN", "ADV"):
        return 0
    elif rgx == "AUX":
        return 3
    elif rgx == "VERB":
        return 2
    else:
        return 4


def determine_ppb(restrictions):
    """ Determine if a word has full meaning - JOS (returns priority). """
    if len(restrictions['POS'][0]) != 1:
        return 0
    category = list(restrictions['POS'][0])[0]
    # rgx = rgxs[0]
    if category in ("adjective", "noun", "adverb"):
        return 0
    elif category == "verb":
        if len(restrictions) == 1:
            return 2
        type = list(restrictions['type'][0])[0] if 'type' in restrictions else ''
        if type == 'auxiliary':
            return 3
        elif type == 'main':
            return 1
        else:
            return 2
    else:
        return 4

class MorphologyRegex:
    """
    Class in charge of morphology JOS restriction regexes.
    """
    def __init__(self, restriction):
        restr_dict = {}
        for feature in restriction:
            feature_dict = dict(feature.items())

            negate = False
            if "filter" in feature_dict:
                assert feature_dict['filter'] == "negative"
                negate = True
                del feature_dict['filter']

            assert len(feature_dict) == 1
            key, value = next(iter(feature_dict.items()))
            if len(value.split('|'))>1:
                print('here')
            restr_dict[key] = (set(value.split('|')), negate)

        assert 'POS' in restr_dict
        self.restrictions = restr_dict

        # # handle multiple word types
        # if '|' in restr_dict['POS'][0]:
        #     categories = restr_dict['POS'][0].split('|')
        # else:
        #     categories = [restr_dict['POS'][0]]
        #
        # self.rgxs = []
        # self.re_objects = []
        # self.min_msd_lengths = []
        #
        # del restr_dict['POS']
        #
        # for category in categories:
        #     min_msd_length = 1
        #     category = category.capitalize()
        #     cat_code = CODES[category]
        #     rgx = [cat_code] + ['.'] * 10
        #
        #     for attribute, (value, neg) in restr_dict.items():
        #         if attribute.lower() not in TAGSET[cat_code]:
        #             continue
        #         index = TAGSET[cat_code].index(attribute.lower())
        #         assert index >= 0
        #
        #         if '|' in value:
        #             match = "".join(CODES[val] for val in value.split('|'))
        #         else:
        #             match = CODES[value]
        #         # if attribute == 'negative':
        #         #     print('aaa')
        #         # if not typ:
        #         #     print('HERE!')
        #
        #         # When typ==False character should be anything but set char.
        #         match = "[{}{}]".format("" if not neg else "^", match)
        #         rgx[index + 1] = match
        #
        #         if not neg:
        #             min_msd_length = max(index + 1, min_msd_length)
        #
        #     # strip rgx
        #     for i in reversed(range(len(rgx))):
        #         if rgx[i] == '.':
        #             rgx = rgx[:-1]
        #         else:
        #             break
        #
        #     self.re_objects.append([re.compile(r) for r in rgx])
        #     self.rgxs.append(rgx)
        #     self.min_msd_lengths.append(min_msd_length)
    
    def __call__(self, text, lemma):
        if not text:
            return False

        properties = msd_to_properties(text, 'en', lemma)

        for res_name, res_val in self.restrictions.items():
            res_name = res_name.lower()

            # handles category
            if res_name == 'pos':
                if not properties.category in res_val[0]:
                    return False

            # handles form other restrictions
            # handles restrictions where we negate filter is off
            elif res_val[1] == False:
                if res_name in properties.form_feature_map:
                    if not properties.form_feature_map[res_name] in res_val[0]:
                        return False
                elif res_name in properties.lexeme_feature_map:
                    if not properties.lexeme_feature_map[res_name] in res_val[0]:
                        return False
                else:
                    return False
            # handle restrictions with negate filter on
            elif res_val[1] == True:
                if res_name in properties.form_feature_map:
                    if properties.form_feature_map[res_name] in res_val[0]:
                        return False
                elif res_name in properties.lexeme_feature_map:
                    if properties.lexeme_feature_map[res_name] in res_val[0]:
                        return False

        return True

class MorphologyUDRegex:
    """
    Class in charge of morphology UD restriction regexes.
    """
    def __init__(self, restriction):
        restr_dict = {}
        for feature in restriction:
            feature_dict = dict(feature.items())

            negate = False
            if "filter" in feature_dict:
                negate = True
                del feature_dict['filter']

            assert len(feature_dict) == 1
            key, value = next(iter(feature_dict.items()))
            restr_dict[key] = (set(value.split('|')), negate)

        assert 'POS' in restr_dict

        self.restrictions = restr_dict

        # # handle multiple word types
        # if '|' in restr_dict['POS'][0]:
        #     categories = restr_dict['POS'][0].split('|')
        # else:
        #     categories = [restr_dict['POS'][0]]



        # self.rgxs = []
        # self.re_objects = []
        # self.min_msd_lengths = []
        #
        # del restr_dict['POS']
        #
        # for category in categories:
        #     min_msd_length = 1
        #     category = category.upper()
        #     assert category in CODES_UD
        #     rgx = category
        #
        #     self.rgxs.append(rgx)
        #     self.min_msd_lengths.append(min_msd_length)

    def __call__(self, msd, lemma):
        udpos = msd.udpos
        if not udpos:
            return False

        for res_name, res_val in self.restrictions.items():
            # res_name = res_name.lower()

            # # handles category
            # if res_name == 'POS':
            #     if not udpos['POS'] in res_val[0]:
            #         return False

            # handles form other restrictions
            # handles restrictions where we negate filter is off
            if res_val[1] == False:
                if res_name in udpos:
                    if not udpos[res_name] in res_val[0]:
                        return False
                else:
                    return False
            # handle restrictions with negate filter on
            elif res_val[1] == True:
                if res_name in udpos:
                    if udpos[res_name] in res_val[0]:
                        return False

        return True

        assert len(self.rgxs) == 1
        return self.rgxs[0] == text


class LexisRegex:
    """
    Class in charge of checking whether lemma is in specified list of words.
    """
    def __init__(self, restriction):
        restr_dict = {}
        for feature in restriction:
            restr_dict.update(feature.items())

        assert "lemma" in restr_dict
        self.match_list = restr_dict['lemma'].split('|')
    
    def __call__(self, text, lemma):
        return text in self.match_list


class SpaceRegex:
    def __init__(self, restriction):
        restr_dict = {}
        for feature in restriction:
            restr_dict.update(feature.items())

        assert "contact" in restr_dict
        self.space = restr_dict['contact'].split('|')
        for el in self.space:
            if el not in ['both', 'right', 'left', 'neither']:
                raise Exception('Value of space restriction is not supported (it may be both, left, right or neither).')

    def __call__(self, word, lemma):
        match = False
        if 'neither' in self.space:
            match = match or (not word.previous_glue and not word.glue)
        if 'left' in self.space:
            match = match or (word.previous_glue and not word.glue)
        if 'right' in self.space:
            match = match or (not word.previous_glue and word.glue)
        if 'both' in self.space:
            match = match or (word.previous_glue and word.glue)

        return match




class Restriction:
    """ A class containing restriction. """
    def __init__(self, restriction_tag, system_type='JOS'):
        self.ppb = 4 # polnopomenska beseda (0-4)

        if restriction_tag is None:
            self.type = RestrictionType.MatchAll
            self.matcher = None
            self.present = None
            return

        restriction_type = restriction_tag.get('type')
        if restriction_type == "morphology":
            if system_type == 'JOS':
                self.type = RestrictionType.Morphology
                self.matcher = MorphologyRegex(list(restriction_tag))
                self.ppb = determine_ppb(self.matcher.restrictions)
            # UD system is handled based on deprel
            elif system_type == 'UD':
                self.type = RestrictionType.MorphologyUD
                self.matcher = MorphologyUDRegex(list(restriction_tag))
            #     self.ppb = determine_ppb_ud(self.matcher.rgxs)

        elif restriction_type == "lexis":
            self.type = RestrictionType.Lexis
            self.matcher = LexisRegex(list(restriction_tag))

        elif restriction_type == "space":
            self.type = RestrictionType.Space
            self.matcher = SpaceRegex(list(restriction_tag))
        else:
            raise NotImplementedError()

    def match(self, word):
        """ Obtains data necessary for matcher and runs it. """
        if self.type == RestrictionType.Morphology:
            match_to = word.xpos
        elif self.type == RestrictionType.MorphologyUD:
            match_to = word
        elif self.type == RestrictionType.Lexis:
            match_to = word.lemma
        elif self.type == RestrictionType.MatchAll:
            return True
        elif self.type == RestrictionType.Space:
            match_to = word
        else:
            raise RuntimeError("Unreachable!")

        return self.matcher(match_to, word.lemma)

