"""
Converter for msd translations and msd conversions to properties
"""
from conversion_utils.jos_msds_and_properties import Converter, Msd, Properties, LEVEL_EXCEPTIONS
from conversion_utils.translate_conllu_jos import get_syn_map

converter = Converter()

syn_map = get_syn_map()


class OptimizedConverter(object):
    def __init__(self):
        self.properties = {category.codes.en.upper(): (category.names.en, [{value.codes.en: (feature.names.en, value.names.en) for value in feature.values} for feature in category.features]) for category in converter.specifications.categories}
        self.lemma_properties = {category.codes.en.upper(): (category.names.en, [{value.codes.en: (feature.names.en, value.names.en) for value in feature.values} for feature in category.features]) for category in converter.specifications.categories}

    def msd_to_properties(self, msd, language, lemma=None, require_valid_flag=False, warn_level_flag=False):
        category_name, category_properties = self.properties[msd[0]]

        properties = {'pos': category_name}
        try:
            for i in range(len(msd) - 1):
                property_char = msd[i + 1]
                if property_char != '-':
                    property_type, property_value = category_properties[i][property_char]
                    properties[property_type] = property_value
            return properties
        except:
            raise 'Msd language might be set incorrectly. Try switching `jos_msd_lang` parameter to `sl`'


optimized_converter = OptimizedConverter()

def msd_to_properties(msd_text, lang, lemma=None):
    """ Converts msd to properties using conversion_utils library. """
    # msd_model = Msd(msd_text, lang)
    return optimized_converter.msd_to_properties(msd_text, lang, lemma=lemma)


def default_msd_to_properties(msd, language, lemma=None, require_valid_flag=False, warn_level_flag=False):
    msd_object = Msd(msd, language)
    return converter.msd_to_properties(msd_object, language, lemma=lemma, require_valid_flag=require_valid_flag, warn_level_flag=warn_level_flag)

def translate_msd(msd_text, lang, lemma=None):
    """ Translates msd using conversion_utils library. """
    if lang == 'en':
        return msd_text
    return converter.properties_to_msd(converter.msd_to_properties(Msd(msd_text, lang), 'en', lemma),
                                       'en').code


def translate_jos_depparse(tag, translate_jos_depparse_to_sl):
    """ Translates jos depparse using conversion_utils library. """
    if not translate_jos_depparse_to_sl:
        return tag
    if tag not in syn_map:
        raise ValueError(f'Tag "{tag}" is not recognized as a valid English tag. You might be using Slovenian depparse system in which case set "jos_depparse_lang" to "sl".')
    return syn_map[tag]
