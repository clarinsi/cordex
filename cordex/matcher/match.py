"""
Class for loading matches
"""
from ast import literal_eval

from cordex.words.word import WordUD, WordJOS


class StructureMatch:
    def __init__(self, match_id, structure):
        self.match_id = str(match_id)
        self.structure = structure

        self.matches = []
        self.representations = {}
    
    @staticmethod
    def from_db(db, collocation_id, structure, is_ud):
        """ Loads matches from database. """
        result = StructureMatch(collocation_id, structure)
        prev_match_id = None

        if is_ud:
            stmt = """SELECT match_id, component_id, word_lemma, word_text, word_udpos, word_id, sentence_id
                      FROM CollocationMatches 
                      JOIN Matches ON Matches.match_id=CollocationMatches.mid_match_id 
                      WHERE mid_collocation_id=? 
                      ORDER BY match_id"""

            for row in db.execute(stmt, (collocation_id,)):
                match_id, component_id, word_lemma, word_text, word_udpos, word_id, sentence_id = row

                if match_id != prev_match_id:
                    result.matches.append({})
                    prev_match_id = match_id

                word_udpos = literal_eval(word_udpos)
                int_word_id = int(word_id) if word_id[0] in '0123456789' else int(word_id[1:])
                result.matches[-1][str(component_id)] = WordUD(word_lemma, '', sentence_id, word_id, int_word_id, word_text, False, feats=word_udpos)

        else:
            stmt = """SELECT match_id, component_id, word_lemma, word_text, word_xpos, word_id, sentence_id
                      FROM CollocationMatches 
                      JOIN Matches ON Matches.match_id=CollocationMatches.mid_match_id 
                      WHERE mid_collocation_id=? 
                      ORDER BY match_id"""

            for row in db.execute(stmt, (collocation_id,)):
                match_id, component_id, word_lemma, word_text, word_xpos, word_id, sentence_id = row

                if match_id != prev_match_id:
                    result.matches.append({})
                    prev_match_id = match_id

                int_word_id = int(word_id) if word_id[0] in '0123456789' else int(word_id[1:])
                result.matches[-1][str(component_id)] = WordJOS(word_lemma, word_xpos, sentence_id, word_id, int_word_id, word_text, False, False)
        
        for component_id, text, msd in db.execute("SELECT component_id, text, msd FROM Representations WHERE collocation_id=?", (collocation_id,)):
            result.representations[str(component_id)] = (text, msd)
        
        return result

    def distinct_forms(self):
        """ Counts all distinct forms. """
        dm = set()
        keys = list(self.matches[0].keys())
        for words in self.matches:
            dm.add(" ".join(words[k].text for k in keys))
        return len(dm)

    def __len__(self):
        return len(self.matches)
