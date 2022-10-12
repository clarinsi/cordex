"""
A class for saving statistics.
"""
from collections import defaultdict, Counter

from ast import literal_eval

from cordex.utils.progress_bar import progress
import logging

class WordStats:
    def __init__(self, args, db):
        self.db = db
        self.is_ud = args['is_ud']
        self.all_words = None

        if self.is_ud:
            self.db.init("""CREATE TABLE UniqWords (
                uw_id INTEGER PRIMARY KEY, 
                lemma varchar(64), 
                udpos varchar(32), 
                text varchar(64), 
                frequency int
                )""")
            self.db.init("CREATE TABLE WordCountUPOS (lemma varchar(64), upos varchar(32), frequency int)")
            self.db.init("CREATE INDEX lemma_msd_text_on_uw ON UniqWords (lemma, udpos, text)")
        else:
            self.db.init("""CREATE TABLE UniqWords (
                            uw_id INTEGER PRIMARY KEY, 
                            lemma varchar(64), 
                            xpos varchar(16), 
                            text varchar(64), 
                            frequency int
                            )""")
            self.db.init("CREATE TABLE WordCountXPOS (lemma varchar(64), xpos0 char, frequency int)")
            self.db.init("CREATE INDEX lemma_msd_text_on_uw ON UniqWords (lemma, xpos, text)")
        self.db.init("CREATE TABLE NumWords (id INTEGER PRIMARY KEY, n INTEGER)")


        self.db.init("CREATE INDEX lemma_on_uw ON UniqWords (lemma)")
        # self.db.init("CREATE INDEX lemma_msd0_on_wc ON WordCount (lemma, msd0)")
        # self.db.init("CREATE INDEX lemma_msd0_on_wc ON WordCount (lemma, msd0)")

    def add_words(self, words):
        """ Adds words to database. """
        for w in progress(words, "adding-words"):
            if w.fake_word:
                continue
            if self.is_ud:
                params = {'lemma': w.lemma, 'udpos': str(w.udpos), 'text': w.text}
                res = self.db.execute("""UPDATE UniqWords SET frequency=frequency + 1
                    WHERE lemma=:lemma AND udpos=:udpos AND text=:text""", params)

                if res.rowcount == 0:
                    self.db.execute("""INSERT INTO UniqWords (lemma, udpos, text, frequency) 
                        VALUES (:lemma, :udpos, :text, 1)""", params)
            else:
                params = {'lemma': w.lemma, 'xpos': str(w.xpos), 'text': w.text}
                res = self.db.execute("""UPDATE UniqWords SET frequency=frequency + 1
                                    WHERE lemma=:lemma AND xpos=:xpos AND text=:text""", params)

                if res.rowcount == 0:
                    self.db.execute("""INSERT INTO UniqWords (lemma, xpos, text, frequency) 
                                        VALUES (:lemma, :xpos, :text, 1)""", params)

        self.db.execute("INSERT INTO NumWords (n) VALUES (?)", (len(words),))

    def num_all_words(self):
        """ Counts all words. """

        if self.all_words is None:
            cur = self.db.execute("SELECT sum(n) FROM NumWords")
            self.all_words = int(cur.fetchone()[0])
        return self.all_words

    def generate_renders(self):
        """ Counts frequencies for lemma + msd combinations. """
        step_name = 'generate_renders'
        if self.db.is_step_done(step_name):
            logging.info("Skipping GenerateRenders, already complete")
            return

        lemmas = [lemma for (lemma, ) in self.db.execute("SELECT DISTINCT lemma FROM UniqWords")]
        for lemma in progress(lemmas, 'word-count'):
            if self.is_ud:
                num_words_upos = defaultdict(int)
                for (udpos, freq) in self.db.execute("SELECT udpos, frequency FROM UniqWords WHERE lemma=?", (lemma,)):
                    upos = literal_eval(udpos)['POS']
                    num_words_upos[upos] += freq

                for upos, freq in num_words_upos.items():
                    self.db.execute("INSERT INTO WordCountUPOS (lemma, upos, frequency) VALUES (?,?,?)",
                        (lemma, upos, freq))

            else:
                num_words_xpos = defaultdict(int)
                for (xpos, freq) in self.db.execute("SELECT xpos, frequency FROM UniqWords WHERE lemma=?", (lemma,)):
                    xpos0 = xpos[0]
                    num_words_xpos[xpos0] += freq

                for xpos0, freq in num_words_xpos.items():
                    self.db.execute("INSERT INTO WordCountXPOS (lemma, xpos0, frequency) VALUES (?,?,?)",
                        (lemma, xpos0, freq))

        self.db.step_is_done(step_name)

    def render(self, lemma, msd):
        """ Returns most frequent word for specific lemma+msd pair. """

        statement = """SELECT msd, frequency FROM UniqWords WHERE 
        lemma=:lemma AND msd=:msd ORDER BY frequency DESC"""

        cur = self.db.execute(statement, {"lemma": lemma, "msd": msd})
        if cur.rowcount > 0:
            return cur.fetchone()[0]

    def available_words(self, lemma, existing_texts):
        """ Lists possible words for agreements and lists them in descending order. """
        counted_texts = Counter(existing_texts)
        for (pos, text), _n in counted_texts.most_common():
            if self.is_ud:
                pos = literal_eval(pos)
            yield (pos, text, lemma)

        if self.is_ud:
            statement = """SELECT udpos, text, frequency FROM UniqWords WHERE 
                        lemma=:lemma ORDER BY frequency DESC"""
            for udpos, text, _f in self.db.execute(statement, {'lemma': lemma}):
                if (udpos, text) not in counted_texts:
                    yield (literal_eval(udpos), text, lemma)
        else:
            statement = """SELECT xpos, text, frequency FROM UniqWords WHERE 
                        lemma=:lemma ORDER BY frequency DESC"""
            for xpos, text, _f in self.db.execute(statement, {'lemma': lemma}):
                if (xpos, text) not in counted_texts:
                    yield (xpos, text, lemma)

    def num_words(self, lemma, msd0):
        """ Returns first word frequency when lemma and msd match. """
        if self.is_ud:
            statement = "SELECT frequency FROM WordCountUPOS WHERE lemma=? AND upos=? LIMIT 1"
        else:
            statement = "SELECT frequency FROM WordCountXPOS WHERE lemma=? AND xpos0=? LIMIT 1"
        cur = self.db.execute(statement, (lemma, msd0))
        result = cur.fetchone()[0]
        return result