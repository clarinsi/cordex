"""
Connections to lexicon via API or file reading
"""
import logging
import lzma
import pickle
import requests
from cordex.utils.codes_tagset import TAGSET, CODES
from cordex.utils.converter import msd_to_properties, default_msd_to_properties
from cordex.utils.progress_bar import progress

SUPPORTED_LOOKUP_LANGUAGES = ['sl']

class LookupApi:
    """ A class for managing API calls. """
    def __init__(self, base_url):
        self.base_url = base_url
        self.forms_data = {}
        self.executed = False
        self.search_lexeme_batch_size = 7500
        self.retrieve_lexeme_batch_size = 500

    def call_api(self, url, json, i, end_i):
        """ Calls api for json[i:end_i]. If response is anything but status code 200, make two calls of halved batch size. """
        response = requests.post(url, json=json[i:end_i])
        if response.status_code != 200:
            new_batch_size = int((end_i - i)/2)
            if new_batch_size < 50:
                raise Exception('Unable to obtain data from API!')
            logging.info(f'{url} with batch size {end_i - i} returned error! Processing with batch size {new_batch_size}')
            response_json = []
            response_json.extend(self.call_api(url, json, i, i + new_batch_size))
            response_json.extend(self.call_api(url, json, i + new_batch_size, end_i))
        else:
            response_json = response.json()
        return response_json
    def search_lexeme(self, post_request):
        """ Executes search-batch request for /search-batch/lexeme/ """
        all_lexemes = []
        batch_size = self.search_lexeme_batch_size
        ran = range(0, len(post_request), batch_size)
        for i in progress(ran,
                          "search lexeme requests", total=len(ran)):
            end_i = min(i + batch_size, len(post_request))

            response_json = self.call_api(self.base_url + '/search-batch/lexeme/', post_request, i, end_i)
            all_lexemes.extend(response_json)
        return all_lexemes

    def retrieve_lexeme(self, post_request):
        """ Executes retrieve-batch request for /retrieve-batch/lexeme/ """
        all_lexemes = []
        batch_size = self.retrieve_lexeme_batch_size
        ran = range(0, len(post_request), batch_size)
        for i in progress(ran,
                          "retrieve lexeme requests", total=len(ran)):
            end_i = min(i + batch_size, len(post_request))
            response_json = self.call_api(self.base_url + f'/retrieve-batch/lexeme/', post_request, i, end_i)
            all_lexemes.extend(response_json)
        return all_lexemes

    def find_lemma(self, lemma_key):
        """ Finds most frequent lemma and its msd based on lemma key. """
        lemma = self.forms_data[lemma_key]['lemma']
        for form in self.forms_data[lemma_key]['forms']:
            if form[0] == lemma:
                return form
        return None

    def find_form(self, lemma_key, form_restrictions):
        """ Finds most frequent proper form based on lemma key and form restrictions. """
        for form in self.forms_data[lemma_key]['forms']:
            match = True
            for k, v in form_restrictions.items():
                k_lowercased = k.lower()
                if k_lowercased not in form[2] or form[2][k_lowercased] != v:
                    match = False
                    break

            if match:
                return form
        return None

    def execute_requests(self, num_representations, db, all_representations):
        """ Creates and executes queries on API from fake representations. """
        post_request = []
        i = 0
        # get data for lexeme post
        for cid, sid in progress(db.execute("SELECT collocation_id, structure_id FROM Collocations"),
                                 "representations-gather-lexeme", total=num_representations):

            representations = all_representations[i]
            for cid, reps in representations.items():
                for rep in reps:
                    if rep.processed_api:
                        for req in rep.api_request:
                            if req['type'] == 'lemma':
                                post_request.append((f"{req['lemma']}_{req['category']}_{'_'.join([f'{k},{v}' for k, v in req['lemma_features'].items()])}", {
                                    'lemma': req['lemma'],
                                    "category": req['category'],
                                    'features': req['lemma_features']
                                }, {'lemma': req['lemma'], 'key': 'lemma'}))
                            elif req['type'] == 'msd' or req['type'] == 'agreement':
                                post_request.append((f"{req['lemma']}_{req['category']}_{'_'.join([f'{k},{v}' for k, v in req['lemma_features'].items()])}", {
                                    'lemma': req['lemma'],
                                    "category": req['category'],
                                    'features': req['lemma_features']
                                }, {'lemma': req['lemma'], 'key': f"{'_'.join([f'{k},{v}' for k, v in req['form_features'].items()])}", 'form_feature': req['form_features']}))
                            else:
                                raise f'req["type"] - {req["type"]} should not exist.'
            i += 1

        # deduplicate post_request
        search_post_request = []
        forms_data = {}
        unique_post_requests = set()
        for el in post_request:
            if el[0] not in unique_post_requests:
                unique_post_requests.add(el[0])
                search_post_request.append(el[1])
                forms_data[el[0]] = {'forms': [], 'lemma': el[1]['lemma']}

        lexeme_responses = self.search_lexeme(search_post_request)

        for form_data_key, lexeme_response in zip(forms_data.keys(), lexeme_responses):
            forms_data[form_data_key]['lexeme_ids'] = [r['id'] for r in lexeme_response['data']]

        retrieve_post_request = [{
                            'lexeme_id': data_el['id'],
                            "msd-language": "en",
                            "extra-data": [ "forms-orthography" ],
                            'corpus_id': 2
                        } for el in lexeme_responses for data_el in el['data']]

        forms_response = self.retrieve_lexeme(retrieve_post_request)

        form_responses_linked = {post_text['lexeme_id']: forms['data'] for post_text, forms in zip(retrieve_post_request, forms_response)}

        # link words and msds with keys
        for lemma_key, lemma_content in forms_data.items():
            complacent_forms = []
            for l_id in lemma_content['lexeme_ids']:
                complacent_forms.extend(form_responses_linked[l_id]['forms'])
            possible_forms = []
            for form in complacent_forms:
                form_features = default_msd_to_properties(form['msd'], 'en', lemma=lemma_content['lemma']).form_feature_map
                for subform in form['forms']:
                    for subsubform in subform:
                        frequency = subsubform['frequency'] if 'frequency' in subsubform and subsubform[
                            'frequency'] else 0
                        possible_forms.append((subsubform['text'], frequency, form_features, form['msd']))

            possible_forms = sorted(possible_forms, key=lambda x: -x[1])
            lemma_content['forms'] = possible_forms

        self.forms_data = forms_data
        self.executed = True

        return forms_data

    @staticmethod
    def deduplicate_post_request(post_request):
        deduplicated_post_request = []
        unique_post_requests = set()
        for el in post_request:
            if el not in unique_post_requests:
                unique_post_requests.add(post_request[0])
                deduplicated_post_request.append(post_request[1])
        return deduplicated_post_request, unique_post_requests

class LookupLexicon:
    """ Object that access lookup lexicon file. """
    def __init__(self, file_path=''):
        self.file_data = None
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
        properties = msd_to_properties(''.join(msd), 'en')
        if properties['pos'] == 'noun':
            if not ('number' in properties and 'case' in properties):
                return decypher
            number = properties['number']
            case = properties['case']
            decypher = {'number': number, 'case': case}
        elif properties['pos'] == 'verb':
            if not ('vform' in properties and 'number' in properties):
                return decypher
            vform = properties['vform']
            number = properties['number']
            person = 'third'
            decypher = {'vform': vform, 'number': number, 'person': person}
        elif properties['pos'] == 'adjective':
            if not ('gender' in properties and 'number' in properties and 'case' in properties):
                return decypher
            gender = properties['gender']
            number = properties['number']
            case = properties['case']
            decypher = {'gender': gender, 'number': number, 'case': case}

        return decypher

    def get_word_form(self, lemma, msd, data, align_msd=False, find_lemma_msd=False):
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
                att_lower = att.lower()
                # some attributes might not have desired properties with which we want alignment
                if att_lower in TAGSET[t_align_msd]:
                    v_align_msd = TAGSET[t_align_msd].index(att_lower)
                    v = TAGSET[t].index(att_lower)
                    # fix for verbs with short msds
                    if v + 1 >= len(msd):
                        msd = msd + ['-' for _ in range(v - len(msd) + 2)]

                    msd[v + 1] = align_msd[v_align_msd + 1]

        # handles cases when we are searching msds of lemmas
        if lemma in self.file_data and find_lemma_msd:
            for (word_form_features, form_representations, xpos, form_frequency) in self.file_data[lemma]:
                if lemma == form_representations:
                    return xpos, lemma, form_representations

        decypher_msd = self.decypher_msd(msd)

        if not decypher_msd:
            return None, None, None

        if lemma in self.file_data:
            for (word_form_features, form_representations, xpos, form_frequency) in self.file_data[lemma]:
                fits = True
                for d_m_attribute, d_m_value in decypher_msd.items():
                    if d_m_attribute not in word_form_features or d_m_value != word_form_features[d_m_attribute]:
                        fits = False
                        break
                if fits:
                    break
            return xpos, lemma, form_representations
        return None, None, None
