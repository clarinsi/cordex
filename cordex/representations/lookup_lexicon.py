"""
Connections to lexicon via API or file reading
"""
import lzma
import pickle
from cordex.utils.codes_tagset import TAGSET, CODES

from cordex.utils.converter import msd_to_properties


class LookupLexicon:
    """ Object that access external data. """
    def __init__(self, use_api, file_path=''):
        self.file_data = None

        if use_api:
            raise NotImplementedError
        else:
            self.init_file_reading(file_path)

    def init_file_reading(self, file_path):
        with lzma.open(file_path, "rb") as f:
            self.file_data = pickle.load(f)

    @staticmethod
    def decypher_msd(msd):
        """ Function that takes xpos tag and returns a dictionary that might be of interest in structures.

        :param msd: Slovenian xpos tag
        :return: Dictionary with attribute names as keys and attribute values as values. (i.e. {'case': 'nominative'})
        """
        decypher = {}
        # msd_model = Msd(''.join(msd), 'en')
        properties = msd_to_properties(''.join(msd), 'en')
        # IF ADDING OR CHANGING ATTRIBUTES HERE ALSO FIX POSSIBLE_WORD_FORM_FEATURE_VALUES
        if properties.category == 'noun':
            number = properties.form_feature_map['number']
            case = properties.form_feature_map['case']
            decypher = {'number': number, 'case': case}
        elif properties.category == 'verb':
            vform = properties.form_feature_map['vform']
            number = properties.form_feature_map['number']
            person = 'third'
            decypher = {'vform': vform, 'number': number, 'person': person}
        elif properties.category == 'adjective':
            gender = properties.form_feature_map['gender']
            number = properties.form_feature_map['number']
            case = properties.form_feature_map['case']
            decypher = {'gender': gender, 'number': number, 'case': case}

        return decypher

    def get_word_form(self, lemma, msd, data, align_msd=False):
        """ Returns word form from lemma and msd that were stored in lookup lexicon. """
        # modify msd as required
        msd = list(msd)
        if 'msd' in data:
            for key, value in data['msd'].items():
                t = msd[0]
                v = TAGSET[t].index(key.lower())
                if v + 1 >= len(msd):
                    msd = msd + ['-' for _ in range(v - len(msd) + 2)]
                msd[v + 1] = CODES[value]

        if align_msd and 'agreement' in data:
            align_msd = list(align_msd)
            t_align_msd = align_msd[0]
            t = msd[0]

            for att in data['agreement']:
                v_align_msd = TAGSET[t_align_msd].index(att.lower())
                v = TAGSET[t].index(att.lower())
                # fix for verbs with short msds
                if v + 1 >= len(msd):
                    msd = msd + ['-' for _ in range(v - len(msd) + 2)]

                msd[v + 1] = align_msd[v_align_msd + 1]

        decypher_msd = self.decypher_msd(msd)

        if not decypher_msd:
            return None, None, None

        if lemma in self.file_data:
            for (word_form_features, form_representations, form_frequency) in self.file_data[lemma]:
                fits = True
                for d_m_attribute, d_m_value in decypher_msd.items():
                    if d_m_attribute not in word_form_features or d_m_value != word_form_features[d_m_attribute]:
                        fits = False
                        break
                if fits:
                    break
            return ''.join(msd), lemma, form_representations
        return None, None, None
