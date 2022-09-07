import csv
import logging
import argparse
import lzma
import pickle
import time
from conversion_utils.jos_msds_and_properties import Msd, Converter

def main(args):
    with open(args.sloleks_csv, newline='', encoding='utf-8') as f:
        sloleks_csv = csv.reader(f, delimiter='|')
        # sloleks_db = csv.reader(f)
        # data = sloleks_db.create_file_from_sloleks()
        next(sloleks_csv, None)

        filtered_sloleks_csv = {}
        for row in sloleks_csv:
            lemma, msd, word_form, frequency = row
            frequency = int(frequency) if frequency else 0
            if (lemma, msd) not in filtered_sloleks_csv or filtered_sloleks_csv[(lemma, msd)]['frequency'] < frequency:
                filtered_sloleks_csv[(lemma, msd)] = {'word_form': word_form, 'frequency': frequency}


        connected_lemmas = {}
        converter = Converter()
        sloleks_len = len(filtered_sloleks_csv)
        progress = 0.01
        for i, (k, v) in enumerate(filtered_sloleks_csv.items()):
            lemma, msd = k
            word_form = v['word_form']
            frequency = v['frequency']
            if lemma not in connected_lemmas:
                connected_lemmas[lemma] = []
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
            if i/sloleks_len > progress:
                print(progress * 100)
                progress += 0.01
            msd = Msd(msd, args.lang)
            properties = converter.msd_to_properties(msd, 'en', lemma=lemma)
            # if properties.form_feature_map:
            #     print('here')
            connected_lemmas[lemma].append((properties.form_feature_map, word_form, frequency))

        # order features by frequency
        for k, v in connected_lemmas.items():
            if len(v) > 1:
                connected_lemmas[k] = sorted(v, reverse=True, key=lambda x: x[2])
    with lzma.open(args.pkl_path, "wb") as f:
        pickle.dump(connected_lemmas, f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Original csv containing 4 columns - lemma, msd, form and frequency.')
    parser.add_argument('--sloleks_csv', type=str, help='Sloleks database credentials')
    parser.add_argument('--pkl_path', type=str, help='Sloleks database credentials')
    parser.add_argument('--lang', type=str, default='sl', help='Sloleks database credentials')
    args = parser.parse_args()

    start = time.time()
    main(args)
    logging.info("TIME: {}".format(time.time() - start))
