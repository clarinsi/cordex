import time
import gc

from corpex.representations.lexicon import Lexicon
from corpex.utils.progress_bar import progress
from corpex.structures.syntactic_structure import build_structures
from corpex.matcher.match_store import MatchStore
from corpex.statistics.word_stats import WordStats
from corpex.writers.writer import Writer
from corpex.readers.loader import load_files
from corpex.database.database import Database
from corpex.utils.time_info import TimeInfo
from conversion_utils.jos_msds_and_properties import Converter

from corpex.postprocessors.postprocessor import Postprocessor
import logging

logger = logging.getLogger('corpex')


class Pipeline:
    def __init__(self, structures, **kwargs):
        kwargs['structures'] = structures
        self.set_default_args(kwargs)

        if self.args['sloleks_db'] is not None:
            self.sloleks_db = Lexicon(False, 'data/lexicon/forms.xz')
        else:
            self.sloleks_db = None

        self.structures, self.max_num_components = build_structures(kwargs)

    def __call__(self, corpus):
        if type(corpus) == str:
            corpus = [corpus]
        self.args['corpus'] = corpus
        time_info = TimeInfo(len(self.args['corpus']))

        database = Database(self.args)
        match_store = MatchStore(self.args, database)
        word_stats = WordStats(database)
        postprocessor = Postprocessor(fixed_restriction_order=self.args['fixed_restriction_order'], lang=self.args['lang'])

        for words in load_files(self.args, database):
            if words is None:
                time_info.add_measurement(-1)
                continue

            start_time = time.time()
            matches = self.match_file(words, self.structures, postprocessor)

            match_store.add_matches(matches)
            word_stats.add_words(words)
            database.commit()

            # force a bit of garbage collection
            del words
            del matches
            gc.collect()

            time_info.add_measurement(time.time() - start_time)
            time_info.info()

        # if no output files, just exit
        if all([x is None for x in [self.args['out']]]):
            return

        # get word renders for lemma/msd
        word_stats.generate_renders()
        match_store.determine_collocation_dispersions()

        # figure out representations!
        match_store.set_representations(word_stats, self.structures, sloleks_db=self.sloleks_db)

        if self.args['statistics']:
            Writer.make_output_writer(self.args, self.max_num_components, match_store, word_stats).write_out(
                self.structures, match_store)
        else:
            Writer.make_output_no_stat_writer(self.args, self.max_num_components, match_store, word_stats).write_out(
                self.structures, match_store)

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
            'verbose': 'info',
            'sort_by': -1,
            'db': None,
            'collocation_sentence_map_dest': None,
            'no_msd_translate': False,
            'multiple_output': False,
            'load_sloleks': False,
            'sort_reversed': False,
            'new_db': False,
            'ignore_punctuations': False,
            'fixed_restriction_order': False,
            'new_tei': False,
            'out': None,
            'statistics': True,
            'lang': 'sl',
            'pos': 'upos'
        }

        self.args = {**default_args, **kwargs}
