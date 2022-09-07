"""
Class for grouping restrictions.
"""
from corpex.restrictions.restriction import Restriction

class RestrictionGroup:
    def __init__(self, restrictions_tag, system_type, group_type='and'):
        self.restrictions = [Restriction(el, system_type) for el in restrictions_tag]
        self.group_type = group_type

    def __iter__(self):
        for restriction in self.restrictions:
            yield restriction

    def match(self, word):
        """ Checks whether sufficient restrictions are met. """
        if self.group_type == 'or':
            for restr in self.restrictions:
                if restr.match(word): # match either
                    return True
            return False
        elif self.group_type == 'and':
            for restr in self.restrictions:
                if not restr.match(word): # match and
                    return False
            return True
        else:
            raise Exception("Unsupported group_type - it may only be 'and' or 'or'")
