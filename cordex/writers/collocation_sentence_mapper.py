""" A file for handling mapper. """

class CollocationSentenceMapper:
    def __init__(self, output_dir):
        self.return_str = False
        if type(output_dir) == bool:
            self.output = []
            self.output.append(['Collocation_id', 'Sentence_id', 'Token_ids'])
            self.return_str = True
            return
        self.output = open(output_dir, "w")
        self.output.write(f'Collocation_id\tSentence_id\tToken_ids\n')

    def get_mapper(self):
        if self.return_str:
            return self.output

    def close(self):
        self.output.close()

    def add_map(self, collocation_id, sentence_id, token_ids):
        """ Adds a new line to output. """
        if self.return_str:
            self.output.append([collocation_id, sentence_id, token_ids])
        else:
            self.output.write(f'{collocation_id}\t{sentence_id}\t{token_ids}\n')
