import time
import gc

from cordex.representations.lookup_lexicon import LookupLexicon
from cordex.utils.progress_bar import progress
from cordex.structures.syntactic_structure import build_structures
from cordex.matcher.match_store import MatchStore
from cordex.statistics.word_stats import WordStats
from cordex.writers.formatter import OutFormatter, OutNoStatFormatter
from cordex.writers.writer import Writer
from cordex.readers.loader import load_files
from cordex.database.database import Database
from cordex.utils.time_info import TimeInfo
from conversion_utils.jos_msds_and_properties import Converter

from cordex.postprocessors.postprocessor import Postprocessor
import logging

logger = logging.getLogger('cordex')


class Pipeline:
    def __init__(self, structures, **kwargs):
        kwargs['structures'] = structures
        self.set_default_args(kwargs)

        if self.args['lookup_lexicon'] is not None:
            self.lookup_lexicon = LookupLexicon(False, self.args['lookup_lexicon'])
        else:
            self.lookup_lexicon = None

        self.structures, self.max_num_components, is_ud = build_structures(self.args)
        # TODO FIX THIS
        self.args['is_ud'] = is_ud

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
        self.word_stats.generate_renders()
        self.match_store.determine_collocation_dispersions()

        # figure out representations!
        self.match_store.set_representations(self.word_stats, self.structures, self.args['is_ud'], lookup_lexicon=self.lookup_lexicon)

        return self

    def write(self, path, collocation_sentence_map_dest=None, separator=',', sort_by=-1, sort_reversed=False, multiple_output=False):
        self.args['out'] = path
        self.args['collocation_sentence_map_dest'] = collocation_sentence_map_dest
        self.args['separator'] = separator
        self.args['sort_by'] = sort_by
        self.args['sort_reversed'] = sort_reversed
        self.args['multiple_output'] = multiple_output

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

    def get_list(self, separator=',', sort_by=-1, sort_reversed=False):
        self.args['separator'] = separator
        self.args['sort_by'] = sort_by
        self.args['sort_reversed'] = sort_reversed

        params = Writer.other_params(self.args)
        if self.args['statistics']:
            writer = Writer(None, self.max_num_components, OutFormatter(self.match_store, self.word_stats, self.args['is_ud']),
                          None, params, self.args['separator'])
        else:
            writer = Writer(None, self.max_num_components,
                            OutNoStatFormatter(self.match_store, self.word_stats, self.args['is_ud']),
                            None, params, self.args['separator'])
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

    def set_default_args(self, kwargs):
        """ Sets default arguments. """
        default_args = {
            'min_freq': 0,
            'db': None,
            'new_db': False,
            # 'collocation_sentence_map_dest': None,
            'no_msd_translate': False,

            # 'sort_reversed': False,
            'ignore_punctuations': False,
            'fixed_restriction_order': False,
            # 'out': None,
            'lookup_lexicon': None,
            'statistics': True,
            'lang': 'sl',
            # 'pos': 'upos',
            'translate_jos_depparse_to_sl': False
        }

        self.args = {**default_args, **kwargs}