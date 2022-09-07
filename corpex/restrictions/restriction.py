"""
Classes for handling restrictions.
"""
import re
from enum import Enum

from corpex.utils.codes_tagset import CODES, TAGSET, CODES_UD


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


def determine_ppb(rgxs):
    """ Determine if a word has full meaning - JOS (returns priority). """
    if len(rgxs) != 1:
        return 0
    rgx = rgxs[0]
    if rgx[0] in ("A", "N", "R"):
        return 0
    elif rgx[0] == "V":
        if len(rgx) == 1:
            return 2
        elif 'a' in rgx[1]:
            return 3
        elif 'm' in rgx[1]:
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

            match_type = True
            if "filter" in feature_dict:
                assert feature_dict['filter'] == "negative"
                match_type = False
                del feature_dict['filter']

            assert len(feature_dict) == 1
            key, value = next(iter(feature_dict.items()))
            restr_dict[key] = (value, match_type)

        assert 'POS' in restr_dict

        # handle multiple word types
        if '|' in restr_dict['POS'][0]:
            categories = restr_dict['POS'][0].split('|')
        else:
            categories = [restr_dict['POS'][0]]

        self.rgxs = []
        self.re_objects = []
        self.min_msd_lengths = []

        del restr_dict['POS']

        for category in categories:
            min_msd_length = 1
            category = category.capitalize()
            cat_code = CODES[category]
            rgx = [cat_code] + ['.'] * 10

            for attribute, (value, typ) in restr_dict.items():
                if attribute.lower() not in TAGSET[cat_code]:
                    continue
                index = TAGSET[cat_code].index(attribute.lower())
                assert index >= 0

                if '|' in value:
                    match = "".join(CODES[val] for val in value.split('|'))
                else:
                    match = CODES[value]

                match = "[{}{}]".format("" if typ else "^", match)
                rgx[index + 1] = match

                if typ:
                    min_msd_length = max(index + 1, min_msd_length)

            # strip rgx
            for i in reversed(range(len(rgx))):
                if rgx[i] == '.':
                    rgx = rgx[:-1]
                else:
                    break

            self.re_objects.append([re.compile(r) for r in rgx])
            self.rgxs.append(rgx)
            self.min_msd_lengths.append(min_msd_length)
    
    def __call__(self, text):
        for i, re_object in enumerate(self.re_objects):
            if len(text) < self.min_msd_lengths[i]:
                continue
            match = True

            for c, r in zip(text, re_object):
                if not r.match(c):
                    match = False
                    break
            if match:
                return True
        return False


class MorphologyUDRegex:
    """
    Class in charge of morphology UD restriction regexes.
    """
    def __init__(self, restriction):
        restr_dict = {}
        for feature in restriction:
            feature_dict = dict(feature.items())

            match_type = True

            assert len(feature_dict) == 1
            key, value = next(iter(feature_dict.items()))
            restr_dict[key] = (value, match_type)

        assert 'POS' in restr_dict

        # handle multiple word types
        if '|' in restr_dict['POS'][0]:
            categories = restr_dict['POS'][0].split('|')
        else:
            categories = [restr_dict['POS'][0]]

        self.rgxs = []
        self.re_objects = []
        self.min_msd_lengths = []

        del restr_dict['POS']

        for category in categories:
            min_msd_length = 1
            category = category.upper()
            assert category in CODES_UD
            rgx = category

            self.rgxs.append(rgx)
            self.min_msd_lengths.append(min_msd_length)

    def __call__(self, text):
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
    
    def __call__(self, text):
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

    def __call__(self, word):
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
                self.ppb = determine_ppb(self.matcher.rgxs)
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
        if self.type == RestrictionType.Morphology or self.type == RestrictionType.MorphologyUD:
            match_to = word.msd
        elif self.type == RestrictionType.Lexis:
            match_to = word.lemma
        elif self.type == RestrictionType.MatchAll:
            return True
        elif self.type == RestrictionType.Space:
            match_to = word
        else:
            raise RuntimeError("Unreachable!")

        return self.matcher(match_to)

