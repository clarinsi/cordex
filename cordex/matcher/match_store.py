"""
A class for storing matches.
"""
import gc
from collections import defaultdict
from ast import literal_eval
from time import time
import logging

from cordex.matcher.match import StructureMatch
from cordex.representations.representation_assigner import RepresentationAssigner
from cordex.utils.progress_bar import progress


class MatchStore:
    def __init__(self, args, db):
        self.db = db
        self.dispersions = {}
        self.min_freq = args['min_freq']
        self.is_ud = args['is_ud']

        # create necessary tables
        self.db.init("""CREATE TABLE Collocations (
            collocation_id INTEGER PRIMARY KEY,
            structure_id varchar(8),
            key varchar(256))
            """)
        if self.is_ud:
            self.db.init("""CREATE TABLE Matches (
                match_id INTEGER,
                component_id INTEGER NOT NULL,
                word_lemma varchar(32) NOT NULL,
                word_id varchar(32) NOT NULL,
                sentence_id varchar(32) NOT NULL,
                word_udpos varchar(32) NOT NULL,
                word_text varchar(32) NOT NULL)
                """)
        else:
            self.db.init("""CREATE TABLE Matches (
                            match_id INTEGER,
                            component_id INTEGER NOT NULL,
                            word_lemma varchar(32) NOT NULL,
                            word_id varchar(32) NOT NULL,
                            sentence_id varchar(32) NOT NULL,
                            word_xpos varchar(16) NOT NULL,
                            word_text varchar(32) NOT NULL)
                            """)
        self.db.init("""CREATE TABLE CollocationMatches (
            mid_match_id INTEGER,
            mid_collocation_id INTEGER,
            FOREIGN KEY(mid_collocation_id) REFERENCES Collocations(collocation_id),
            FOREIGN KEY(mid_match_id) REFERENCES Matches(match_id))
            """)
        self.db.init("""CREATE TABLE Representations (
            collocation_id INTEGER,
            component_id INTEGER,
            text varchar(32),
            msd varchar(32),
            FOREIGN KEY(collocation_id) REFERENCES Collocations(collocation_id))
            """)
        self.db.init("""CREATE TABLE Dispersions (
            structure_id varchar(64),
            component_id varchar(64),
            lemma varchar(128),
            dispersion INTEGER)
            """)
        
        self.db.init("CREATE INDEX key_sid_c ON Collocations (key, structure_id)")
        self.db.init("CREATE INDEX sid_c ON Collocations (structure_id)")
        self.db.init("CREATE INDEX mmid_cm ON CollocationMatches (mid_collocation_id)")
        self.db.init("CREATE INDEX mid_m ON Matches (match_id)")
        self.db.init("CREATE INDEX col_r ON Representations (collocation_id)")
        self.db.init("CREATE INDEX disp_key ON Dispersions (structure_id, component_id, lemma)")

        match_num = self.db.execute("SELECT MAX(match_id) FROM Matches").fetchone()[0]
        self.match_num = 0 if match_num is None else match_num + 1

    def _add_match(self, key, match):
        """ Inserts a match to database. """
        structure_id, key_str = key[0], str(key[1:])
        cid = self.db.execute("SELECT collocation_id FROM Collocations WHERE key=? AND structure_id=?",
                              (key_str, structure_id)).fetchone()

        if cid is None:
            self.db.execute("INSERT INTO Collocations (structure_id, key) VALUES (?,?)",
                            (structure_id, key_str))
            cid = self.db.execute("SELECT collocation_id FROM Collocations WHERE key=? AND structure_id=?",
                                  (key_str, structure_id)).fetchone()
        
        for component_id, word in match.items():
            if self.is_ud:
                self.db.execute("""
                INSERT INTO Matches (match_id, component_id, word_lemma, word_text, word_udpos, word_id, sentence_id) 
                VALUES (:match_id, :component_id, :word_lemma, :word_text, :word_udpos, :word_id, :sentence_id)""", {
                    "component_id": component_id,
                    "match_id": self.match_num,
                    "word_lemma": word.lemma,
                    "word_udpos": str(word.udpos),
                    "word_text": word.text,
                    "word_id": word.id,
                    "sentence_id": word.sentence_id,
                })
            else:
                self.db.execute("""
                INSERT INTO Matches (match_id, component_id, word_lemma, word_text, word_xpos, word_id, sentence_id) 
                VALUES (:match_id, :component_id, :word_lemma, :word_text, :word_xpos, :word_id, :sentence_id)""", {
                    "component_id": component_id,
                    "match_id": self.match_num,
                    "word_lemma": word.lemma,
                    "word_xpos": word.xpos,
                    "word_text": word.text,
                    "word_id": word.id,
                    "sentence_id": word.sentence_id,
                })

        self.db.execute("INSERT INTO CollocationMatches (mid_collocation_id, mid_match_id) VALUES (?,?)",
                        (cid[0], self.match_num))
        
        self.match_num += 1

    def add_matches(self, matches):
        """ Add multiple matches. """
        for structure, nms in progress(matches.items(), 'adding-matches'):
            for nm in nms:
                self._add_match(nm[1], nm[0])

    def get_matches_for(self, structure):
        """ Get all matches for given structure. """
        for cid in self.db.execute("SELECT collocation_id FROM Collocations WHERE structure_id=?",
                                   (structure.id,)):
            yield StructureMatch.from_db(self.db, cid[0], structure, self.is_ud)

    def add_inserts(self, inserts):
        """ Adds representations to database. """

        for match in inserts:
            for component_id, (text, msd) in match.representations.items():
                self.db.execute("""
                    INSERT INTO Representations (collocation_id, component_id, text, msd) 
                    VALUES (?,?,?,?)""", (match.match_id, component_id, text, msd))

    def set_representations(self, word_renderer, structures, is_ud, lookup_lexicon=None, lookup_api=False):
        """ Adds representations to matches. """

        step_name = 'representation'
        if self.db.is_step_done(step_name):
            logging.info("Representation step already done, skipping")
            return

        num_inserts = 1000
        inserts = []

        structures_dict = {s.id: s for s in structures}
        num_representations = int(self.db.execute("SELECT Count(*) FROM Collocations").fetchone()[0])

        # preprocess when api is used
        all_representations = []
        if lookup_api:
            # create api queries
            for cid, sid in progress(self.db.execute("SELECT collocation_id, structure_id FROM Collocations"),
                                     "representations", total=num_representations):
                structure = structures_dict[sid]
                match = StructureMatch.from_db(self.db, cid, structure, is_ud)
                representations = {}
                RepresentationAssigner.set_representations(match, word_renderer, is_ud, representations,
                                                           lookup_lexicon=lookup_lexicon, lookup_api=lookup_api)

                all_representations.append(representations)

            # get data results
            lookup_api.execute_requests(num_representations, self.db, all_representations)

        start_time = time()
        i = 0
        for cid, sid in progress(self.db.execute("SELECT collocation_id, structure_id FROM Collocations"), "representations", total=num_representations):
            structure = structures_dict[sid]
            match = StructureMatch.from_db(self.db, cid, structure, is_ud)
            representations = {}
            RepresentationAssigner.set_representations(match, word_renderer, is_ud, representations, lookup_lexicon=lookup_lexicon, lookup_api=lookup_api)

            inserts.append(match)
            if len(inserts) > num_inserts:
                self.add_inserts(inserts)
                inserts = []
            if time() - start_time > 5:
                start_time = time()
                gc.collect()
            if lookup_api:
                all_representations.append(representations)
            i += 1
        self.add_inserts(inserts)

        self.db.step_is_done(step_name)

    def frequency_filter(self, collocation_id):
        """ Filters by frequency. """

        matches = self.db.execute("SELECT MIN(MAX(COUNT(*), ?), ?) FROM CollocationMatches WHERE mid_collocation_id=?", (self.min_freq - 1, self.min_freq, collocation_id)).fetchone()[0]
        return matches >= self.min_freq

    def determine_collocation_dispersions(self):
        """ Allocates collocation dispersions. """
        step_name = 'dispersions'
        if self.db.is_step_done(step_name):
            self.load_dispersions()
            return

        dispersions = defaultdict(int)
        for collocation_id, structure_id, word_tups_str in progress(self.db.execute("SELECT collocation_id, structure_id, key FROM Collocations"), "dispersion"):
            if not self.frequency_filter(collocation_id):
                continue

            word_tups = literal_eval(word_tups_str)
            for component_id, lemma in word_tups:
                dispersions[(str(structure_id), component_id, lemma)] += 1
            
        self.dispersions = dict(dispersions)
        logging.info("Storing dispersions...")
        self.store_dispersions()

        self.db.step_is_done(step_name)

    def store_dispersions(self):
        """ Stores dispersions in sql database. """
        for (structure_id, component_id, lemma), disp in self.dispersions.items():
            self.db.execute("INSERT INTO Dispersions (structure_id, component_id, lemma, dispersion) VALUES (?, ?, ?, ?)",
                            (structure_id, component_id, lemma, disp))

    def load_dispersions(self):
        """ Load dispersions when they are in database. """
        self.dispersions = {}
        for structure_id, component_id, lemma, dispersion in progress(self.db.execute("SELECT * FROM Dispersions"), "load-dispersions"):
            self.dispersions[structure_id, component_id, lemma] = dispersion
