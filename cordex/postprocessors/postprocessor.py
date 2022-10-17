"""
Custom processing after matching.
"""


class Postprocessor:
    def __init__(self, fixed_restriction_order=False, lang='sl'):
        self.fixed_restriction_order = fixed_restriction_order
        self.lang = lang

    @staticmethod
    def fix_sz_sl(next_word):
        """ Fixes s/z in Slovenian. """
        if next_word[0] in ['c', 'č', 'f', 'h', 'k', 'p', 's', 'š', 't']:
            return 's'
        return 'z'

    @staticmethod
    def fix_kh_sl(next_word):
        """ Fixes k/h in Slovenian. """
        if next_word[0] in ['g', 'k']:
            return 'h'
        return 'k'

    def process(self, match, collocation_id):
        """ Runs Slovenian k/h and s/z fixes. """
        if self.lang != 'sl':
            return match, collocation_id

        if len(collocation_id) > 2:
            for idx, (col_id, word) in enumerate(collocation_id[1:-1]):
                if word in ['s', 'z']:
                    correct_letter = self.fix_sz_sl(collocation_id[idx + 2][1])
                    collocation_id[idx + 1][1] = correct_letter
                    match[col_id].text = correct_letter
                elif word in ['k', 'h']:
                    correct_letter = self.fix_kh_sl(collocation_id[idx + 2][1])
                    collocation_id[idx + 1][1] = correct_letter
                    match[col_id].text = correct_letter
        collocation_id = [collocation_id[0]] + [tuple(line) for line in collocation_id[1:]]
        return match, collocation_id

    def is_fixed_restriction_order(self, match):
        """ If necessary, checks if restrictions are in correct order. """

        if not self.fixed_restriction_order:
            return True

        sorted_dict = {k: v for k, v in sorted(match.items(), key=lambda item: item[1].int_id)}
        prev_id = -1
        for key in sorted_dict.keys():
            if key == '#':
                continue
            int_key = int(key)
            if prev_id > int_key:
                return False
            prev_id = int_key

        return True
