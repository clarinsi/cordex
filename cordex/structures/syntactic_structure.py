"""
Default syntactic structure class.
"""

from xml.etree import ElementTree
import logging

from cordex.utils.codes_tagset import PPB_DEPRELS
from cordex.structures.component import Component, ComponentType


class SyntacticStructure:
    def __init__(self):
        self.id = None
        # self.lbs = None
        self.components = []
        self.fake_root_included = False

    @staticmethod
    def from_xml(xml, no_stats, is_ud):
        """ Reads a syntactic structure from xml. """
        st = SyntacticStructure()
        st.id = xml.get('id')
        if st.id is None:
            st.id = xml.get('tempId')

        components, dependencies, definitions = list(xml)

        deps = [(dep.get('from'), dep.get('to'), dep.get('label'), dep.get('order'))
                for dep in dependencies]
        comps = {comp.get('cid'): dict(comp.items()) for comp in components}

        restrs, forms = {}, {}

        for comp in definitions:
            n = comp.get('cid')
            restrs[n] = []
            forms[n] = []

            for el in comp:
                if el.tag.startswith("restriction"):
                    restrs[n].append(el)
                elif el.tag.startswith("representation"):
                    st.add_representation(n, el, forms)
                else:
                    raise NotImplementedError("Unknown definition: {} in structure {}"
                                              .format(el.tag, st.id))

        # creates fake root component onto which other components are appended.
        fake_root_component = Component({'cid': '#', 'type': 'other', 'restriction': None}, is_ud)
        fake_root_component_children = fake_root_component.create_children(deps, comps, restrs, forms)

        # all dep with value modra point to artificial root - fake_root_component
        if any([dep[2] == 'modra' for dep in deps]):
            st.fake_root_included = True
            st.components = [fake_root_component] + fake_root_component_children
        else:
            st.components = fake_root_component_children

        if not no_stats:
            if is_ud:
                st.determine_core2w_ud()
            else:
                st.determine_core2w()

        return st

    def determine_core2w_ud(self):
        """ Determines two core words in UD collocation. """
        deprels = {}
        for c in self.components:
            for next_el in c.children:
                deprels[next_el[0]] = next_el[1]
        ppb_components_num = 0
        for c in self.components:
            if c.type != ComponentType.Core:
                continue
            if c in deprels and deprels[c] not in PPB_DEPRELS:
                continue
            ppb_components_num += 1
            c.type = ComponentType.Core2w

        assert ppb_components_num == 2, RuntimeError("Cannot determine 2 'jedrna polnopomenska beseda' for", self.id)

    def determine_core2w(self):
        """ Determines two core words in JOS collocation. """
        ppb_components = []
        for c in self.components:
            if c.type != ComponentType.Core:
                continue

            ppb = 4
            for r in c.restrictions:
                ppb = min(r.ppb, ppb)

            ppb_components.append((c, ppb))

        ppb_components = sorted(ppb_components, key=lambda ch: ch[1])
        if len(ppb_components) > 2 and ppb_components[1][1] == ppb_components[2][1]:
            raise RuntimeError("Cannot determine 2 'jedrna polnopomenska beseda' for", self.id)

        for c, _ in ppb_components[:2]:
            c.type = ComponentType.Core2w

    def add_representation(self, n, rep_el, forms):
        """ Adds representation to syntactic structure. """
        assert rep_el.tag == "representation"
        to_add = []
        for el in rep_el:
            assert el.tag == "feature"
            if 'rendition' in el.attrib or 'selection' in el.attrib or 'format' in el.attrib:
                to_add.append(el)
            else:
                logging.warning("Strange representation feature in structure {}. Skipping"
                                .format(self.id))
                continue
        forms[n].append(to_add)

    def match(self, word):
        matches = self.components[0].match(word)
        return [] if matches is None else matches


def build_structures(args):
    """ Builds structures. """
    filename = args['structures']
    no_stats = not args['statistics']

    max_num_components = -1
    with open(filename, 'r', encoding="UTF-8") as fp:
        et = ElementTree.XML(fp.read())

    assert 'system_type' in et.attrib, ValueError('Please update file containing structure descriptions.')
    is_ud = et.attrib['system_type'] == 'UD'
    structures = []
    for structure in et.iter('syntactic_structure'):
        if not ((structure.attrib['type'] == 'collocation' and 'formal_descendants' not in structure.attrib) or structure.attrib['type'] == 'formal'):
            continue
        to_append = SyntacticStructure.from_xml(structure, no_stats, is_ud)
        if to_append is None:
            continue

        structures.append(to_append)
        to_append_len = len(to_append.components) if not to_append.fake_root_included else len(to_append.components) - 1
        max_num_components = max(max_num_components, to_append_len)

    return structures, max_num_components, is_ud
