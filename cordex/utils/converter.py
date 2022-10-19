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

    def msd_to_properties(self, msd, language, lemma=None, require_valid_flag=False, warn_level_flag=False):


        # if type(msd) == Msd:
        #     msd = msd.code

        # self.check_valid_msd(msd, require_valid_flag)
        category_name, category_properties = self.properties[msd[0]]

        properties = {'pos': category_name}

        for i in range(len(msd) - 1):
            property_char = msd[i + 1]
            if property_char != '-':
                property_type, property_value = category_properties[i][property_char]
                properties[property_type] = property_value
        # properties = {msd[i + 1] for i in range(len(msd) - 1)}
        #
        # category_char = msd[0]
        # value_chars = msd.code[1:]
        # category = converter.specifications.find_category_by_code(category_char, msd.language)
        # category_name = category.names.get(language)
        # feature_value_list = []
        # lexeme_feature_map = {}
        # form_feature_map = {}
        # for (index, value_char) in enumerate(value_chars, start=1):
        #     if (value_char != '-'):
        #         feature = category.find_feature_by_position(index)
        #         value = feature.find_value_by_char(value_char, msd.language)
        #         feature_name = feature.names.get(language)
        #         feature_value = value.names.get(language)
        #         if (warn_level_flag and lemma is None and (category_name, index) in [(le[0], le[1]) for le in
        #                                                                              LEVEL_EXCEPTIONS]):
        #             print(
        #                 '[WARN] The level (lexeme vs form) of feature (category={category}, position={position}) may be incorrect, as it is lemma-specific and no lemma has been specified.'
        #                 .format(category=category_name, position=index))
        #         level_exception_flag = (category_name, feature.position, lemma) in LEVEL_EXCEPTIONS
        #         lexeme_level_flag = feature.lexeme_level_flag if not level_exception_flag else not feature.lexeme_level_flag
        #         feature_value_list.append((feature, value))
        #         if (lexeme_level_flag):
        #             lexeme_feature_map[feature_name] = feature_value
        #         else:
        #             form_feature_map[feature_name] = feature_value
        return properties


optimized_converter = OptimizedConverter()

def msd_to_properties(msd_text, lang, lemma=None):
    """ Converts msd to properties using conversion_utils library. """
    # msd_model = Msd(msd_text, lang)
    return optimized_converter.msd_to_properties(msd_text, lang, lemma=lemma)


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
    return syn_map[tag]
