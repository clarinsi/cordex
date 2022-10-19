"""
Classes for handling restrictions.
"""
from enum import Enum
from cordex.utils.converter import msd_to_properties


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
            restr_dict[key] = (set(value.split('|')), negate)

        assert 'POS' in restr_dict
        self.restrictions = restr_dict

    def __call__(self, text, lemma):
        if not text:
            return False

        properties = msd_to_properties(text, 'en', lemma)

        for res_name, res_val in self.restrictions.items():
            res_name = res_name.lower()

            # handles category
            if res_name == 'pos':
                if properties['pos'] not in res_val[0]:
                    return False

            # handles form other restrictions
            # handles restrictions where we negate filter is off
            elif res_val[1] == False:
                if res_name in properties:
                    if not properties[res_name] in res_val[0]:
                        return False
                else:
                    return False
            # handle restrictions with negate filter on
            elif res_val[1] == True:
                if res_name in properties:
                    if properties[res_name] in res_val[0]:
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

    def __call__(self, msd, lemma):
        udpos = msd.udpos
        if not udpos:
            return False

        for res_name, res_val in self.restrictions.items():
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
    def __init__(self, restriction_tag, is_ud):
        self.ppb = 4  # polnopomenska beseda (0-4)

        if restriction_tag is None:
            self.type = RestrictionType.MatchAll
            self.matcher = None
            self.present = None
            return

        restriction_type = restriction_tag.get('type')
        if restriction_type == "morphology":
            # UD system is handled based on deprel
            if is_ud:
                self.type = RestrictionType.MorphologyUD
                self.matcher = MorphologyUDRegex(list(restriction_tag))
            #     self.ppb = determine_ppb_ud(self.matcher.rgxs)
            else:
                self.type = RestrictionType.Morphology
                self.matcher = MorphologyRegex(list(restriction_tag))
                self.ppb = determine_ppb(self.matcher.restrictions)

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
