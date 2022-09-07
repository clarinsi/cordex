"""
A class for saving statistics.
"""
from collections import defaultdict, Counter

from corpex.utils.progress_bar import progress
import logging

class WordStats:
    def __init__(self, db):
        self.db = db
        self.all_words = None

        self.db.init("""CREATE TABLE UniqWords (
            uw_id INTEGER PRIMARY KEY, 
            lemma varchar(64), 
            msd varchar(16), 
            text varchar(64), 
            frequency int
            )""")
        self.db.init("CREATE TABLE WordCount (lemma varchar(64), msd0 char, frequency int)")
        self.db.init("CREATE TABLE NumWords (id INTEGER PRIMARY KEY, n INTEGER)")

        self.db.init("CREATE INDEX lemma_msd_text_on_uw ON UniqWords (lemma, msd, text)")
        self.db.init("CREATE INDEX lemma_on_uw ON UniqWords (lemma)")
        self.db.init("CREATE INDEX lemma_msd0_on_wc ON WordCount (lemma, msd0)")

    def add_words(self, words):
        """ Adds words to database. """
        for w in progress(words, "adding-words"):
            if w.fake_word:
                continue
            params = {'lemma': w.lemma, 'msd': w.msd, 'text': w.text}
            res = self.db.execute("""UPDATE UniqWords SET frequency=frequency + 1
                WHERE lemma=:lemma AND msd=:msd AND text=:text""", params)

            if res.rowcount == 0:
                self.db.execute("""INSERT INTO UniqWords (lemma, msd, text, frequency) 
                    VALUES (:lemma, :msd, :text, 1)""", params)

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
            num_words = defaultdict(int)
            for (msd, freq) in self.db.execute("SELECT msd, frequency FROM UniqWords WHERE lemma=?", (lemma,)):
                num_words[msd[0]] += freq
                
            for msd0, freq in num_words.items():
                self.db.execute("INSERT INTO WordCount (lemma, msd0, frequency) VALUES (?,?,?)",
                    (lemma, msd0, freq))

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
        for (msd, text), _n in counted_texts.most_common():
            yield (msd, text)

        statement = """SELECT msd, text, frequency FROM UniqWords WHERE 
        lemma=:lemma ORDER BY frequency DESC"""
        for msd, text, _f in self.db.execute(statement, {'lemma': lemma}):
            if (msd, text) not in counted_texts:
                yield (msd, text)
    
    def num_words(self, lemma, msd0):
        """ Returns first word frequency when lemma and msd match. """
        statement = "SELECT frequency FROM WordCount WHERE lemma=? AND msd0=? LIMIT 1"
        cur = self.db.execute(statement, (lemma, msd0))
        result = cur.fetchone()[0]
        return result
