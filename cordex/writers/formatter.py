"""
A file in charge of properly formatting output text.
"""
from math import log2
import re
import logging

from cordex.structures.component import ComponentType


class Formatter:
    def __init__(self, collocation_ids, word_renderer, is_ud, args):
        self.collocation_ids = collocation_ids
        self.word_renderer = word_renderer
        self.is_ud = is_ud
        self.decimal_separator = args['decimal_separator']
        self.args = args
        self.additional_init()
    
    def header_repeat(self):
        raise NotImplementedError("Header repeat formatter not implemented")

    def header_right(self):
        raise NotImplementedError("Header right formatter not implemented")

    def content_repeat(self, words, representations, idx, sidx):
        raise NotImplementedError("Content repeat formatter not implemented")

    def content_right(self, freq):
        raise NotImplementedError("Content right formatter not implemented")
    
    def additional_init(self):
        pass

    def length(self):
        return len(self.header_repeat())

    def set_structure(self, structure):
        pass

    def new_match(self, match):
        pass


class OutNoStatFormatter(Formatter):
    """
    Formats regular output text without statistics.
    """
    def additional_init(self):
        self.representation = {}

    def header_repeat(self):
        """ Returns no stats header that occurs multiple times. """
        return ["Lemma", "Representative_form", "RF_msd", "RF_scenario"]
    
    def header_right(self):
        """ Returns no stats header for columns that occur one time. """
        return ["Joint_representative_form_fixed", "Joint_representative_form_variable", "Frequency"]
    
    def content_repeat(self, words, representations, idx, _sidx):
        """ Returns no stats content for columns that might appear multiple times. """
        word = words[idx]
        if idx not in representations:
            return ["", "", ""]

        rep_text, rep_msd = representations[idx]
        if rep_text is None:
            self.representation[idx] = word.lemma
            return [word.lemma, word.lemma, "", "lemma_fallback"]
        else:
            self.representation[idx] = rep_text
            return [word.lemma, rep_text, rep_msd, "ok"]

    def content_right(self, freq, variable_word_order=None):
        """ Returns no stats content for columns that occur one time. """
        fixed_word_order = sorted(self.representation.keys())
        if variable_word_order is None:
            variable_word_order = fixed_word_order
        rep_fixed_word_order = ' '.join([self.representation[o] for o in fixed_word_order if o in self.representation])
        rep_variable_word_order = ' '.join([self.representation[o] for o in variable_word_order if o in self.representation])
        result = [rep_fixed_word_order, rep_variable_word_order, str(freq)]
        self.representation = {}
        return result
    
    def __str__(self):
        return "out-no-stat"


class StatsFormatter(Formatter):
    """
    Formats text for statistics.
    """
    def additional_init(self):
        self.stats = None
        self.jppb = None
        self.corew = None
    
    @staticmethod
    def stat_str(num, decimal_separator):
        string = "{:.5f}".format(num) if isinstance(num, float) else str(num)
        if decimal_separator != '.':
            string = string.replace('.', decimal_separator)
        return string
    
    def set_structure(self, structure):
        """ Gets full meaning words positions from structure. """
        jppb = []
        corew = []

        for component in structure.components:
            if component.type == ComponentType.Core2w:
                jppb.append(component.idx)
            if component.type != ComponentType.Other:
                corew.append(component.idx)

        assert(len(jppb) == 2)
        self.jppb = tuple(jppb)
        self.corew = tuple(corew)
    
    def new_match(self, match):
        """ Calculates statistics for a match. """
        self.stats = {"freq": {}}

        for cid in self.corew:
            if cid not in match.matches[0]:
                freq = 0
            else:
                word = match.matches[0][cid]
                if self.is_ud:
                    word_msd0 = word.udpos['POS']
                else:
                    word_msd0 = word.xpos[0]

                freq = self.word_renderer.num_words(word.lemma, word_msd0)

            self.stats["freq"][cid] = freq

        fx = self.stats["freq"][self.jppb[0]]
        fy = self.stats["freq"][self.jppb[1]]
        freq = len(match)
        N = self.word_renderer.num_all_words()

        self.stats['d12'] = freq / fx - (fy - freq) / (N - fx)
        self.stats['d21'] = freq / fy - (fx - freq) / (N - fy)

        self.stats['df'] = match.distinct_forms()
        self.stats['freq_all'] = freq

    def header_repeat(self):
        """ Returns stats header that occurs multiple times. """
        return ["Distribution"]
    
    def header_right(self):
        """ Returns stats header that occur one time only. """
        return ["Delta_p12", "Delta_p21", "LogDice_core", "LogDice_all", "Distinct_forms"]
    
    def content_repeat(self, words, representations, idx, sidx):
        """ Returns stats for columns that might appear multiple times. """
        # not a core word
        if idx not in self.corew:
            return [""] * self.length()

        word = words[idx]
        key = (sidx, idx, word.lemma)
        # try to fix missing dispersions
        if key not in self.collocation_ids.dispersions:
            if word.lemma == 'k':
                new_key = (sidx, idx, 'h')
            elif word.lemma == 'h':
                new_key = (sidx, idx, 'k')
            elif word.lemma == 's':
                new_key = (sidx, idx, 'z')
            elif word.lemma == 'z':
                new_key = (sidx, idx, 's')
            else:
                new_key = (sidx, idx, '')
            if new_key in self.collocation_ids.dispersions:
                key = new_key
                logging.info('Dispersions fixed.')
            else:
                logging.info('Dispersions not fixed.')
        if key in self.collocation_ids.dispersions:
            distribution = self.collocation_ids.dispersions[key]
        else:
            distribution = 1
        return [self.stat_str(distribution, self.decimal_separator)]
    
    def content_right(self, freq):
        """ Returns stats for columns that occur one time only. """
        fx = self.stats["freq"][self.jppb[0]]
        fy = self.stats["freq"][self.jppb[1]]
        freq = self.stats['freq_all']
        logdice_core = 14 + log2(2 * freq / (fx + fy))

        fi = [self.stats["freq"][idx] for idx in self.corew]
        fi = [f for f in fi if f > 0]
        logdice_all = 14 + log2(len(fi) * freq / sum(fi))

        return [self.stat_str(x, self.decimal_separator) for x in (
            self.stats["d12"], self.stats["d21"], logdice_core, logdice_all, self.stats['df']
        )]
    
    def __str__(self):
        return "stat"

class OutFormatter(Formatter):
    """
    Formats regular output text.
    """
    def additional_init(self):
        self.f1 = OutNoStatFormatter(self.collocation_ids, self.word_renderer, self.is_ud, self.args)
        self.f2 = StatsFormatter(self.collocation_ids, self.word_renderer, self.is_ud, self.args)

    def header_repeat(self):
        """ Combines and returns no stats header with stats header on columns that might appear multiple times. """
        return self.f1.header_repeat() + self.f2.header_repeat()

    def header_right(self):
        """ Combines and returns no stats header with stats header columns that occur one time. """
        return self.f1.header_right() + self.f2.header_right()

    def content_repeat(self, words, representations, idx, sidx, variable_word_order=None):
        """ Combines no stats content with stats content on columns that might appear multiple times. """
        cr1 = self.f1.content_repeat(words, representations, idx, sidx)
        cr2 = self.f2.content_repeat(words, representations, idx, sidx)
        return cr1 + cr2

    def content_right(self, freq, variable_word_order=None):
        """ Combines no stats content with stats content on columns that appear only once. """
        return self.f1.content_right(freq, variable_word_order) + self.f2.content_right(freq)

    def set_structure(self, structure):
        """ Sets structure where necessary. """
        self.f2.set_structure(structure)

    def new_match(self, match):
        """ Formats output from a match. """
        self.f2.new_match(match)
    
    def __str__(self):
        return "out"
