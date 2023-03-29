"""
Classes related to syntactic structure components.
"""
from enum import Enum

from cordex.structures.order import Order
from cordex.representations.representation_assigner import RepresentationAssigner
from cordex.restrictions.restriction_group import RestrictionGroup


class ComponentStatus(Enum):
    Optional = 0
    Required = 1
    Forbidden = 2


class ComponentType(Enum):
    Other = 0
    Core = 2
    Core2w = 3


class Component:
    def __init__(self, info, is_ud):
        idx = info['cid']
        name = info['label'] if 'label' in info else None
        typ = ComponentType.Core if info['type'] == "core" else ComponentType.Other

        if 'status' not in info:
            status = ComponentStatus.Required
        elif info['status'] == 'forbidden':
            status = ComponentStatus.Forbidden
        elif info['status'] == 'obligatory':
            status = ComponentStatus.Required
        elif info['status'] == 'optional':
            status = ComponentStatus.Optional
        else:
            raise NotImplementedError("strange status: {}".format(info['status']))

        self.is_ud = is_ud
        self.status = status
        self.name = name
        self.idx = idx
        self.restrictions = RestrictionGroup([None], self.is_ud) if 'restriction' in info else []
        self.children = []
        self.representation = []
        self.selection = {}
        self.type = typ

        self.iter_ctr = 0

    def add_child(self, child_component, link_label, order):
        """ Adds next component"""
        self.children.append((child_component, link_label, Order.new(order)))

    def set_restriction(self, restrictions_tags):
        """ Set regex restrictions to component. """
        if not restrictions_tags:
            self.restrictions = RestrictionGroup([None], self.is_ud)

        # if first element is of type restriction all following are as well
        elif restrictions_tags[0].tag == "restriction":
            self.restrictions = RestrictionGroup(restrictions_tags, self.is_ud)

        # combinations of 'and' and 'or' restrictions are currently not implemented
        elif restrictions_tags[0].tag == "restriction_or":
            self.restrictions = RestrictionGroup(restrictions_tags[0], self.is_ud, group_type='or')

        else:
            raise RuntimeError("Unreachable")

    def set_representation(self, representation):
        """ Set component representation. """
        for rep in representation:
            crend = RepresentationAssigner()
            for feature in rep:
                crend.add_feature(feature.attrib)
            self.representation.append(crend)

    def create_children(self, deps, comps, restrs, reprs):
        """ Create component children. """
        to_ret = []
        for d in deps:
            if d[0] == self.idx:
                _, idx, dep_label, order = d

                child = Component(comps[idx], self.is_ud)
                child.set_restriction(restrs[idx])
                child.set_representation(reprs[idx])
                to_ret.append(child)

                self.add_child(child, dep_label, order)
                others = child.create_children(deps, comps, restrs, reprs)
                to_ret.extend(others)

        return to_ret

    def match(self, word):
        """ Returns list of words that match restrictions. When no words are found return None. """
        # check self restrictions
        m1 = self._match_self(word)
        if m1 is None:
            return None

        # check next node
        mn = self._match_next(word)
        if mn is None:
            return None

        to_ret = [m1]
        for cmatch in mn:
            # if good match but nothing to add, just continue
            if len(cmatch) == 0:
                continue

            # create new to_ret, to which extend all results
            new_to_ret = []
            for tr in to_ret:
                # make sure that one word is not used twice in same to_ret
                new_to_ret.extend([{**dict(tr), **m} for m in cmatch if all([m_v not in dict(tr).values() for m_v in m.values()])])
            if len(new_to_ret) == 0:
                return None
            to_ret = new_to_ret
            del new_to_ret

        return to_ret

    def _match_self(self, word):
        """ Checks restrictions of root word. """
        # matching
        if self.restrictions.match(word):
            return {self.idx: word}

    def _match_next(self, word):
        """ Matches for every component in links from this component """
        to_ret = []

        # need to get all links that match
        for next, link, order in self.children:
            next_links = word.get_links(link)
            to_ret.append([])

            # good flag
            good = next.status != ComponentStatus.Required
            for next_word in next_links:
                if not order.match(word, next_word):
                    continue

                match = next.match(next_word)

                if match is not None:
                    # special treatment for forbidden
                    if next.status == ComponentStatus.Forbidden:
                        good = False
                        break

                    else:
                        assert type(match) is list
                        to_ret[-1].extend(match)
                        good = True

            # if none matched, nothing found!
            if not good:
                return None

        return to_ret
