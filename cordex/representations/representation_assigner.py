"""
Class for assigning representations.
"""

from cordex.representations.representation import ComponentRepresentation, LemmaCR, LexisCR, WordFormAgreementCR, WordFormAnyCR, WordFormMsdCR, WordFormAllCR


class RepresentationAssigner:
    def __init__(self):
        self.more = {}
        self.representation_factory = ComponentRepresentation

    def add_feature(self, feature):
        """ Sets up a proper representation factory, depending on feature. """
        if 'rendition' in feature:
            if feature['rendition'] == "lemma":
                self.representation_factory = LemmaCR
            elif feature['rendition'] == "word_form":
                # just by default, changes with selection
                self.representation_factory = WordFormAnyCR
            elif feature['rendition'] == "lexis":
                self.representation_factory = LexisCR
                self.more['lexis'] = feature['string']
            else:
                raise NotImplementedError("Representation rendition: {}".format(feature))

        elif 'selection' in feature:
            if feature['selection'] == "msd":
                # could already be agreement
                if self.representation_factory != WordFormAgreementCR:
                    self.representation_factory = WordFormMsdCR
                self.more['msd'] = {k: v for k, v in feature.items() if k != 'selection'}
            elif feature['selection'] == "all":
                self.representation_factory = WordFormAllCR
            elif feature['selection'] == 'agreement':
                assert feature['msd'] is not None
                self.representation_factory = WordFormAgreementCR
                self.more['agreement'] = feature['msd'].split('+')
                self.more['other'] = feature['head_cid']
            else:
                raise NotImplementedError("Representation selection: {}".format(feature))
        elif 'format' in feature:
            self.more['format'] = feature['format']

    def create_component_representation(self, word_renderer):
        """ Creates component representation. """
        return self.representation_factory(self.more, word_renderer)

    @staticmethod
    def set_representations(match, word_renderer, is_ud, representations, lookup_lexicon=None, lookup_api=False):
        """ Assigns representations to words. """
        for c in match.structure.components:
            representations[c.idx] = []
            for rep in c.representation:
                representations[c.idx].append(rep.create_component_representation(word_renderer))

        # links agreement representations with representations
        for cid, reps in representations.items():
            for rep in reps:
                for agr in rep.get_agreement_head_component_id():
                    if len(representations[agr]) != 1:
                        n = len(representations[agr])
                        raise NotImplementedError(
                            "Structure {}: ".format(match.structure.id) +
                            "component {} has agreement".format(cid) +
                            " with component {}".format(agr) +
                            ", however there are {} (!= 1) representations".format(n) +
                            " of component {}!".format(agr))

                    representations[agr][0].agreement.append(rep)

        # links matches with representations
        for words in match.matches:
            # first pass, check everything but agreements
            for w_id, w in words.items():
                component_representations = representations[w_id]
                for representation in component_representations:
                    representation.add_word(w, is_ud)

        for cid, reps in representations.items():
            for rep in reps:
                rep.render(is_ud, lookup_lexicon=lookup_lexicon, lookup_api=lookup_api)

        for cid, reps in representations.items():
            reps_text = [rep.rendition_text for rep in reps]
            reps_msd = [rep.rendition_msd for rep in reps]
            if reps_text == []:
                pass
            elif all(r is None for r in reps_text):
                match.representations[cid] = (None, None)
            else:
                reps_text_joined = " ".join(("" if r is None else r) for r in reps_text)
                reps_msd_joined = " ".join(("" if r is None else r) for r in reps_msd)
                match.representations[cid] = (reps_text_joined, reps_msd_joined)
