import gc

from corpex.utils.codes_tagset import TAGSET, CODES, CODES_TRANSLATION, POSSIBLE_WORD_FORM_FEATURE_VALUES


class SloleksDatabase:
    def __init__(self, db, load_sloleks):
        from psycopg2cffi import compat
        compat.register()

        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import Session
        from sqlalchemy import create_engine

        global Lexeme, LexemeFeature, SyntacticStructure, StructureComponent, Feature, LexicalUnitLexeme, LexicalUnit, LexicalUnitType, Category, Sense, Measure, LexicalUnitMeasure, Corpus, Definition, WordForm, WordFormFeature, FormRepresentation, FormEncoding
        [db_user, db_password, db_database, db_host] = db.split(':')

        engine = create_engine('postgresql://' + db_user + ':' + db_password + '@' + db_host + '/' + db_database,
                               pool_recycle=14400)
        Base = declarative_base()
        Base.metadata.reflect(engine)

        class Lexeme(Base):
            __table__ = Base.metadata.tables['jedro_lexeme']

        class LexemeFeature(Base):
            __table__ = Base.metadata.tables['jedro_lexeme_feature']

        class SyntacticStructure(Base):
            __table__ = Base.metadata.tables['jedro_syntacticstructure']

        class StructureComponent(Base):
            __table__ = Base.metadata.tables['jedro_structurecomponent']

        class Feature(Base):
            __table__ = Base.metadata.tables['jedro_feature']

        class LexicalUnitLexeme(Base):
            __table__ = Base.metadata.tables['jedro_lexicalunit_lexeme']

        class LexicalUnit(Base):
            __table__ = Base.metadata.tables['jedro_lexicalunit']

        class LexicalUnitType(Base):
            __table__ = Base.metadata.tables['jedro_lexicalunittype']

        class Category(Base):
            __table__ = Base.metadata.tables['jedro_category']

        class Sense(Base):
            __table__ = Base.metadata.tables['jedro_sense']

        class Measure(Base):
            __table__ = Base.metadata.tables['jedro_measure']

        class LexicalUnitMeasure(Base):
            __table__ = Base.metadata.tables['jedro_lexicalunitmeasure']

        class Corpus(Base):
            __table__ = Base.metadata.tables['jedro_corpus']

        class Definition(Base):
            __table__ = Base.metadata.tables['jedro_definition']

        class WordForm(Base):
            __table__ = Base.metadata.tables['jedro_wordform']

        class WordFormFeature(Base):
            __table__ = Base.metadata.tables['jedro_wordform_feature']

        class FormRepresentation(Base):
            __table__ = Base.metadata.tables['jedro_formrepresentation']

        class FormEncoding(Base):
            __table__ = Base.metadata.tables['jedro_formencoding']

        self.session = Session(engine)

        self.load_sloleks = load_sloleks
        if self.load_sloleks:
            self.init_load_sloleks()

    # def init_load_sloleks2(self):


    def init_load_sloleks(self):
        query_word_form_features = self.session.query(WordFormFeature.word_form_id, WordFormFeature.value)
        word_form_features = query_word_form_features.all()
        query_form_representations = self.session.query(FormRepresentation.word_form_id)
        form_representations = query_form_representations.all()
        query_form_encoding = self.session.query(FormEncoding.form_representation_id, FormEncoding.text)
        form_encodings = query_form_encoding.all()
        query_word_forms = self.session.query(WordForm.id, WordForm.lexeme_id)
        word_forms = query_word_forms.all()
        query_lexemes = self.session.query(Lexeme.id, Lexeme.lemma)
        lexemes = query_lexemes.all()

        self.lemmas = {}
        for lexeme in lexemes:
            if lexeme.lemma not in self.lemmas:
                self.lemmas[lexeme.lemma] = []
            self.lemmas[lexeme.lemma].append(lexeme.id)

        self.word_form_features = {}
        for word_form_feature in word_form_features:
            if word_form_feature.value not in POSSIBLE_WORD_FORM_FEATURE_VALUES:
                continue
            if word_form_feature.word_form_id not in self.word_form_features:
                self.word_form_features[word_form_feature.word_form_id] = set()
            self.word_form_features[word_form_feature.word_form_id].add(word_form_feature.value)

        form_encodings_dict = {form_encoding.form_representation_id: form_encoding.text for form_encoding
                                     in form_encodings}

        self.form_representations = {form_representation.word_form_id: form_encodings_dict[form_representation.word_form_id] for form_representation
                                     in form_representations}

        self.word_forms = {}
        for word_form in word_forms:
            if word_form.lexeme_id not in self.word_forms:
                self.word_forms[word_form.lexeme_id] = []
            self.word_forms[word_form.lexeme_id].append(word_form.id)


        self.connected_lemmas = {}
        for lemma, lemma_ids in self.lemmas.items():
            for lemma_id in lemma_ids:
                if lemma_id in self.word_forms:
                    for word_form_id in self.word_forms[lemma_id]:
                        if word_form_id in self.word_form_features and word_form_id in self.form_representations:
                            if lemma not in self.connected_lemmas:
                                self.connected_lemmas[lemma] = []
                            self.connected_lemmas[lemma].append((self.word_form_features[word_form_id], self.form_representations[word_form_id]))

        del self.lemmas, self.word_form_features, self.form_representations, self.word_forms
        gc.collect()


    def close(self):
        self.session.close()

    def decypher_msd(self, msd):
        t = msd[0]
        decypher = []
        # IF ADDING OR CHANGING ATTRIBUTES HERE ALSO FIX POSSIBLE_WORD_FORM_FEATURE_VALUES
        if t == 'N':
            # gender = CODES_TRANSLATION[t][2][msd[2]]
            number = CODES_TRANSLATION[t][3][msd[3]]
            case = CODES_TRANSLATION[t][4][msd[4]]
            decypher = [number, case]
        elif t == 'V':
            # gender = CODES_TRANSLATION[t][6][msd[6]]
            vform = CODES_TRANSLATION[t][3][msd[3]]
            number = CODES_TRANSLATION[t][5][msd[5]]
            person = 'third'
            decypher = [vform, number, person]
        elif t == 'A':
            gender = CODES_TRANSLATION[t][3][msd[3]]
            number = CODES_TRANSLATION[t][4][msd[4]]
            case = CODES_TRANSLATION[t][5][msd[5]]
            decypher = [gender, number, case]

        return decypher

    def get_word_form(self, lemma, msd, data, align_msd=False):
        # modify msd as required
        from sqlalchemy.orm import aliased
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

        if self.load_sloleks and lemma in self.connected_lemmas:
            for (word_form_features, form_representations) in self.connected_lemmas[lemma]:
                fits = True
                for d_m in decypher_msd:
                    if d_m not in word_form_features:
                        fits = False
                        break
                if fits:
                    break
            return ''.join(msd), lemma, form_representations
        else:
            wfs = [aliased(WordFormFeature) for _ in decypher_msd]
            # self.session.query(FormEncoding.form_representation_id, FormEncoding.text)
            query_preposition = self.session.query(FormEncoding.text) \
                .join(FormRepresentation, FormRepresentation.id == FormEncoding.form_representation_id) \
                .join(WordForm, WordForm.id == FormRepresentation.word_form_id) \
                .join(Lexeme, Lexeme.id == WordForm.lexeme_id)
            # query_preposition = self.session.query(FormRepresentation.form) \
            #     .join(WordForm, WordForm.id == FormRepresentation.word_form_id) \
            #     .join(Lexeme, Lexeme.id == WordForm.lexeme_id)

            for wf in wfs:
                query_preposition = query_preposition.join(wf, wf.word_form_id == WordForm.id)

            query_preposition = query_preposition.filter(Lexeme.lemma == lemma)

            for wf, msd_el in zip(wfs, decypher_msd):
                query_preposition = query_preposition.filter(wf.value == msd_el)

            pattern_translation_hws = query_preposition.limit(1).all()
            if len(pattern_translation_hws) > 0:
                return ''.join(msd), lemma, pattern_translation_hws[0][0]
        return None, None, None
