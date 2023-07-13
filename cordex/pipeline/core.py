import os
import time
import gc
from pathlib import Path

from cordex.representations.lookup import LookupLexicon, SUPPORTED_LOOKUP_LANGUAGES, LookupApi
from cordex.utils.progress_bar import progress
from cordex.structures.syntactic_structure import build_structures
from cordex.matcher.match_store import MatchStore
from cordex.statistics.word_stats import WordStats
from cordex.writers.formatter import OutFormatter, OutNoStatFormatter
from cordex.writers.writer import Writer
from cordex.readers.loader import load_files
from cordex.database.database import Database
from cordex.utils.time_info import TimeInfo

from cordex.postprocessors.postprocessor import Postprocessor
import logging

logger = logging.getLogger('cordex')

HOME_DIR = str(Path.home())

class Pipeline:
    def __init__(self, structures, **kwargs):
        kwargs['structures'] = structures
        self.args = self.set_default_args(kwargs)

        self.structures, self.max_num_components, is_ud = build_structures(self.args)
        self.args['is_ud'] = is_ud

        if self.args['lookup_api'] and not is_ud:
            self.lookup_api = LookupApi('https://blisk.ijs.si/api')
            self.lookup_lexicon = None
        elif self.args['lookup_lexicon'] is not None and os.path.exists(self.args['lookup_lexicon']) and not is_ud:
            self.lookup_lexicon = LookupLexicon(self.args['lookup_lexicon'])
            self.lookup_api = None
        else:
            self.lookup_lexicon = None
            self.lookup_api = None

        if not self.lookup_lexicon and self.args['lang'] in SUPPORTED_LOOKUP_LANGUAGES and not is_ud:
            logger.warning(f'WARNING: Results could be improved if you include lookup lexicon (or provide correct path '
                           f'to it using `lookup_lexicon` argument). '
                           f'You may download it using `cordex.download()`. If it is stored in different location than '
                           f'`{HOME_DIR}/cordex_resources` you should add path to `lookup_lexicon` argument.')

    def __call__(self, corpus):
        if type(corpus) == str:
            corpus = [corpus]
        self.args['corpus'] = corpus
        time_info = TimeInfo(len(self.args['corpus']))

        database = Database(self.args)
        self.match_store = MatchStore(self.args, database)
        self.word_stats = WordStats(self.args, database)
        postprocessor = Postprocessor(fixed_restriction_order=self.args['fixed_restriction_order'], lang=self.args['lang'])

        for words in load_files(self.args, database):
            if words is None:
                time_info.add_measurement(-1)
                continue

            start_time = time.time()
            matches = self.match_file(words, self.structures, postprocessor)

            # adds results to database
            self.match_store.add_matches(matches)
            self.word_stats.add_words(words)
            database.commit()

            # force a bit of garbage collection
            del words
            del matches
            gc.collect()

            time_info.add_measurement(time.time() - start_time)
            time_info.info()

        # get word renders for lemma/msd
        self.word_stats.lowercase_words_under_threshold()
        self.word_stats.generate_renders()
        self.match_store.determine_collocation_dispersions()

        # figure out representations!
        self.match_store.set_representations(self.word_stats, self.structures, self.args['is_ud'], lookup_lexicon=self.lookup_lexicon, lookup_api=self.lookup_api)

        return self

    def write(self, path, separator='\t', sort_by=-1, sort_reversed=False, decimal_separator='.'):
        self.args['out'] = path
        self.args['separator'] = separator
        self.args['decimal_separator'] = decimal_separator
        self.args['sort_by'] = sort_by
        self.args['sort_reversed'] = sort_reversed
        self.args['multiple_output'] = '.' not in Path(path).name

        # if no output files, just exit
        if all([x is None for x in [self.args['out']]]):
            return

        if self.args['statistics']:
            Writer.make_output_writer(self.args, self.max_num_components, self.match_store, self.word_stats,
                                      self.args['is_ud']).write_out(
                self.structures, self.match_store)
        else:
            Writer.make_output_no_stat_writer(self.args, self.max_num_components, self.match_store, self.word_stats,
                                              self.args['is_ud']).write_out(
                self.structures, self.match_store)

    def get_list(self, separator='\t', sort_by=-1, sort_reversed=False, decimal_separator='.'):
        self.args['separator'] = separator
        self.args['decimal_separator'] = decimal_separator
        self.args['sort_by'] = sort_by
        self.args['sort_reversed'] = sort_reversed
        self.args['multiple_output'] = False

        params = Writer.other_params(self.args)
        if self.args['statistics']:
            writer = Writer(None, self.max_num_components, OutFormatter(self.match_store, self.word_stats, self.args['is_ud'], self.args),
                            self.args['collocation_sentence_map_dest'], params, self.args['separator'])
        else:
            writer = Writer(None, self.max_num_components,
                            OutNoStatFormatter(self.match_store, self.word_stats, self.args['is_ud'], self.args),
                            self.args['collocation_sentence_map_dest'], params, self.args['separator'])
        return writer.write_out(self.structures, self.match_store, return_list=True)

    @staticmethod
    def match_file(words, structures, postprocessor):
        """ Looks for collocations inside a file that match structure restrictions. """
        matches = {s: [] for s in structures}

        for s in progress(structures, "matching"):
            for w in words:
                mhere = s.match(w)
                for match in mhere:
                    if not postprocessor.is_fixed_restriction_order(match):
                        continue
                    collocation_id = [[idx, w.lemma] for idx, w in match.items()]
                    collocation_id = [s.id] + list(sorted(collocation_id, key=lambda x: x[0]))
                    match, collocation_id = postprocessor.process(match, collocation_id)
                    collocation_id = tuple(collocation_id)

                    matches[s].append((match, collocation_id))

        return matches

    @staticmethod
    def set_default_args(kwargs):
        """ Sets default arguments. """
        lang = 'sl'
        default_args = {
            'min_freq': 0,
            'db': None,
            'overwrite_db': False,
            'jos_msd_lang': 'en',
            'ignore_punctuations': False,
            'fixed_restriction_order': False,
            'lookup_lexicon': f'{HOME_DIR}/cordex_resources/{lang}.xz',
            'lookup_api': False,
            'statistics': True,
            'lang': 'sl',
            'collocation_sentence_map_dest': None,
            'jos_depparse_lang': 'sl'
        }

        return {**default_args, **kwargs}
