"""
A file for forming and saving outputs.
"""
import logging
import os
import shutil
from pathlib import Path

from cordex.utils.progress_bar import progress
from cordex.writers.formatter import OutFormatter, OutNoStatFormatter
from cordex.writers.collocation_sentence_mapper import CollocationSentenceMapper


class Writer:
    @staticmethod
    def other_params(args):
        """ Obtains and formats parameters that are needed for initialization of Writer class. """
        return (args['multiple_output'], int(args['sort_by']), args['sort_reversed'], args['min_freq'])

    @staticmethod
    def make_output_writer(args, num_components, collocation_ids, word_renderer, is_ud):
        """ Returns an instance of Writer class with classical settings. """
        params = Writer.other_params(args)
        return Writer(args['out'], num_components, OutFormatter(collocation_ids, word_renderer, is_ud, args), args['collocation_sentence_map_dest'], params, args['separator'])

    @staticmethod
    def make_output_no_stat_writer(args, num_components, collocation_ids, word_renderer, is_ud):
        """ Returns an instance of Writer class with settings for no statistics output. """
        params = Writer.other_params(args)
        return Writer(args['out'], num_components, OutNoStatFormatter(collocation_ids, word_renderer, is_ud, args), args['collocation_sentence_map_dest'], params, args['separator'])

    def __init__(self, file_out, num_components, formatter, collocation_sentence_map_dest, params, separator):
        self.collocation_sentence_map_dest = collocation_sentence_map_dest
        if params is None:
            self.multiple_output = False
            self.sort_by = -1
            self.sort_order = None
            self.min_frequency = 1
        else:
            self.multiple_output = params[0]
            self.sort_by = params[1]
            self.sort_order = params[2]
            self.min_frequency = params[3]

        self.num_components = num_components
        self.output_file = file_out
        self.formatter = formatter
        self.separator = separator

    def header(self):
        """ Forms header content in a list with repeating columns first and one off columns after. """
        repeating_cols = self.formatter.header_repeat()
        cols = ["C{}_{}".format(i + 1, thd) for i in range(self.num_components) 
                for thd in repeating_cols]

        cols = ["Structure_ID"] + cols + ["Collocation_ID"]
        cols += self.formatter.header_right()
        return cols

    def sorted_rows(self, rows):
        """ Sorts rows by specified column. """
        if self.sort_by < 0 or len(rows) < 2:
            return rows

        if len(rows[0]) <= self.sort_by:
            logging.warning("Cannot sort by column #{}: Not enough columns!".format(len(rows[0])))
            return rows

        try:
            int(rows[0][self.sort_by])

            def key(row): 
                return int(row[self.sort_by])
        except ValueError:
            def key(row): 
                return row[self.sort_by].lower()

        return sorted(rows, key=key, reverse=self.sort_order)

    def write_header(self, file_handler, return_list):
        """ Writes header to output. """
        if return_list:
            return self.header()
        else:
            file_handler.write(self.separator.join(self.header()) + "\n")

    def write_out_worker(self, file_handler, structure, collocation_ids, col_sent_map, return_list):
        rows = []
        components = structure.components
        for match in collocation_ids.get_matches_for(structure):
            if len(match) < self.min_frequency:
                continue

            self.formatter.new_match(match)

            variable_word_order = self.find_variable_word_order(match.matches)

            if col_sent_map is not None:
                for words in match.matches:
                    token_ids = []
                    for int_i in range(1, len(words) + 1):
                        str_i = str(int_i)
                        if str_i in words:
                            token_ids.append(f'{words[str_i].sentence_id}.{words[str_i].id}')
                    col_sent_map.add_map(match.match_id, words['1'].sentence_id, '|'.join(token_ids))

            for words in match.matches:
                to_write = []

                idx = 1
                for _comp in components:
                    if _comp.idx == '#':
                        continue
                    idx_s = str(idx)
                    idx += 1
                    if idx_s not in words:
                        to_write.extend([""] * self.formatter.length())
                    else:
                        to_write.extend(self.formatter.content_repeat(words, match.representations, idx_s, structure.id))

                # make them equal size
                to_write.extend([""] * (self.num_components * self.formatter.length() - len(to_write)))

                # structure_id and collocation_id
                to_write = [structure.id] + to_write + [match.match_id]

                # header_right
                to_write.extend(self.formatter.content_right(len(match), variable_word_order))
                rows.append(to_write)
                break

        if rows != []:
            rows = self.sorted_rows(rows)
            if return_list:
                return [row for row in rows]
            else:
                file_handler.write("\n".join([self.separator.join(row) for row in rows]) + "\n")
                file_handler.flush()

        else:
            if return_list:
                return []

    def write_out(self, structures, collocation_ids, return_list=False):
        """ Writes processing results to file. """
        write_results = []

        if self.output_file is None and not return_list:
            return

        def fp_close(fp_):
            fp_.close()

        def fp_open(snum=None):
            if snum is None:
                return open(self.output_file, "w", encoding="UTF-8")
            else:
                return open("{}.csv".format(os.path.join(self.output_file, snum)), "w", encoding="UTF-8")

        # erase file/folder if exists
        if type(self.collocation_sentence_map_dest) == str and os.path.exists(self.collocation_sentence_map_dest):
            if os.path.isdir(self.collocation_sentence_map_dest):
                shutil.rmtree(self.collocation_sentence_map_dest)
            else:
                os.remove(self.collocation_sentence_map_dest)


        if not self.multiple_output:

            if return_list:
                write_results.append(self.header())
            else:
                fp = fp_open()
                self.write_header(fp, return_list)
            col_sent_map = CollocationSentenceMapper(self.collocation_sentence_map_dest) \
                if self.collocation_sentence_map_dest else None

        for s in progress(structures, "writing:{}".format(self.formatter)):
            if self.multiple_output:

                if return_list:
                    write_results.append(self.header())
                else:
                    fp = fp_open(s.id)
                    self.write_header(fp, return_list)
                if self.collocation_sentence_map_dest:
                    Path(self.collocation_sentence_map_dest).mkdir(parents=True, exist_ok=True)
                col_sent_map = CollocationSentenceMapper(os.path.join(self.collocation_sentence_map_dest, f'{s.id}.tsv')) \
                    if self.collocation_sentence_map_dest else None

            self.formatter.set_structure(s)
            if return_list:
                content = self.write_out_worker(None, s, collocation_ids, col_sent_map, return_list)
                write_results.extend(content)
            else:
                self.write_out_worker(fp, s, collocation_ids, col_sent_map, return_list)

                if self.multiple_output:
                    fp_close(fp)

        if not return_list:
            if not self.multiple_output:
                fp_close(fp)
            if col_sent_map:
                col_sent_map.close()

        if return_list and self.collocation_sentence_map_dest:
            if col_sent_map.get_mapper() is None:
                logging.warning("If you want to get collocation sentence map, you should set `collocation_sentence_map_dest` to True")
            return write_results, col_sent_map.get_mapper()

        if type(self.collocation_sentence_map_dest) == bool and self.collocation_sentence_map_dest:
            logging.error(
                "You should put path into `collocation_sentence_map_dest`. It can only be set to `True` if you are using `get_list()` function.")
        return write_results

    @staticmethod
    def find_variable_word_order(matches):
        """ Returns word order that has seen the most occurrences. """
        orders = {}
        for words in matches:
            order = tuple([tup[0] for tup in sorted(words.items(), key=lambda x: x[1].int_id)])
            orders[order] = orders.get(order, 0) + 1
        return max(orders, key=orders.get)
