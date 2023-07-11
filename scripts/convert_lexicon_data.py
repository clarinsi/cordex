import csv
import logging
import argparse
import lzma
import pickle
import time
from conversion_utils.jos_msds_and_properties import Msd, Converter

from cordex.utils.converter import translate_msd


def fix_msd(msd, word_form):
    if msd == 'Rdn':
        print(f'{word_form} : {msd}')
        msd = 'Rd'
    if msd == 'Gp-spdzd':
        print(f'{word_form} : {msd}')
        msd = 'Gp-spdzn'
    if msd == 'Gp-spmzn':
        print(f'{word_form} : {msd}')
        msd = 'Gp-spm-n'
    if msd == 'Gp-spmzd':
        print(f'{word_form} : {msd}')
        msd = 'Gp-spm-d'
    if msd == 'Gp-ppdzn':
        print(f'{word_form} : {msd}')
        msd = 'Gp-ppd-n'
    if msd == 'Gp-ppdzd':
        print(f'{word_form} : {msd}')
        msd = 'Gp-ppd-d'
    if msd == 'Gp-ppmzn':
        print(f'{word_form} : {msd}')
        msd = 'Gp-ppm-n'
    if msd == 'Gp-ppmzd':
        print(f'{word_form} : {msd}')
        msd = 'Gp-ppm-d'
    if msd == 'Gp-pdd-d':
        print(f'{word_form} : {msd}')
        msd = 'Gp-pdd-n'
    if msd == 'Gp-pdm-d':
        print(f'{word_form} : {msd}')
        msd = 'Gp-pdm-n'
    if msd == 'Gp-ptd-d':
        print(f'{word_form} : {msd}')
        msd = 'Gp-ptd-n'
    if msd == 'Kagmei':
        print(f'{word_form} : {msd}')
        msd = 'Kag'
    if msd == 'Kbgmei':
        print(f'{word_form} : {msd}')
        msd = 'Kbgmdi'
    return msd


def main(args):
    with open(args.sloleks_csv, newline='', encoding='utf-8') as f:
        sloleks_csv = csv.reader(f, delimiter='|')
        next(sloleks_csv, None)

        filtered_sloleks_csv = {}
        unique_lemma_msds = {}
        for row in sloleks_csv:
            lemma, msd, word_form, frequency = row
            frequency = int(frequency) if frequency else 0
            if (lemma, msd) not in filtered_sloleks_csv or filtered_sloleks_csv[(lemma, msd)]['frequency'] < frequency:
                filtered_sloleks_csv[(lemma, msd)] = {'word_form': word_form, 'frequency': frequency}
            if lemma not in unique_lemma_msds or unique_lemma_msds[lemma]['frequency'] < frequency:
                if word_form == lemma:
                    unique_lemma_msds[lemma] = {'word_form': word_form, 'frequency': frequency, 'msd': msd}


        connected_lemmas = {}
        converter = Converter()
        sloleks_len = len(filtered_sloleks_csv)
        progress = 0.01
        # appending distinct lemma+word_form combinations
        print('Processing lemma+word_form combinations')
        for i, (k, v) in enumerate(filtered_sloleks_csv.items()):
            lemma, msd = k
            word_form = v['word_form']
            frequency = v['frequency']
            if lemma not in connected_lemmas:
                connected_lemmas[lemma] = []
            msd = fix_msd(msd, word_form)
            if i/sloleks_len > progress:
                print(progress * 100)
                progress += 0.01
            msd_obj = Msd(msd, args.lang)
            properties = converter.msd_to_properties(msd_obj, 'en', lemma=lemma)
            msd = translate_msd(msd, 'sl', lemma=lemma)
            connected_lemmas[lemma].append((properties.form_feature_map, word_form, msd, frequency))

        # appending distinct unique lemma msds
        print('Processing distinct lemmas')
        progress = 0.01
        for i, (k, v) in enumerate(unique_lemma_msds.items()):
            lemma = k
            msd = v['msd']
            word_form = v['word_form']
            frequency = v['frequency']
            if lemma not in connected_lemmas:
                connected_lemmas[lemma] = []
            msd = fix_msd(msd, word_form)
            if i/sloleks_len > progress:
                print(progress * 100)
                progress += 0.01
            msd_obj = Msd(msd, args.lang)
            properties = converter.msd_to_properties(msd_obj, 'en', lemma=lemma)
            msd = translate_msd(msd, 'sl', lemma=lemma)
            already_present = False
            for el in connected_lemmas[lemma]:
                if el[1] == word_form and el[2] == msd and el[3] == frequency:
                    already_present = True
            if not already_present:
                connected_lemmas[lemma].append((properties.form_feature_map, word_form, msd, frequency))

        # order features by frequency
        for k, v in connected_lemmas.items():
            if len(v) > 1:
                connected_lemmas[k] = sorted(v, reverse=True, key=lambda x: x[3])
    with lzma.open(args.output, "wb") as f:
        pickle.dump(connected_lemmas, f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='A script that prepares and formats lookup lexicon for cordex.')
    parser.add_argument('--sloleks_csv', type=str, help='Path to csv containing data saved as lemma|msd|form|frequency.')
    parser.add_argument('--output', type=str, help='Path to output file that will be used by cordex.')
    parser.add_argument('--lang', type=str, default='sl', help='Language of msds ("sl" or "en").')
    args = parser.parse_args()

    start = time.time()
    main(args)
    logging.info("TIME: {}".format(time.time() - start))
