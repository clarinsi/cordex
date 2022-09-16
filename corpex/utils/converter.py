"""
Converter for msd translations and msd conversions to properties
"""
from conversion_utils.jos_msds_and_properties import Converter, Msd

converter = Converter()


def msd_to_properties(msd_text, lang, lemma=None):
    msd_model = Msd(msd_text, lang)
    return converter.msd_to_properties(msd_model, lang, lemma=lemma)
