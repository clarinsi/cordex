"""
Converter for msd translations and msd conversions to properties
"""
from conversion_utils.jos_msds_and_properties import Converter, Msd
from conversion_utils.translate_conllu_jos import get_syn_map

converter = Converter()
syn_map = get_syn_map()


def msd_to_properties(msd_text, lang, lemma=None):
    """ Converts msd to properties using conversion_utils library. """
    msd_model = Msd(msd_text, lang)
    return converter.msd_to_properties(msd_model, lang, lemma=lemma)


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
