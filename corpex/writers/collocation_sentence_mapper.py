""" A file for handling mapper. """

class CollocationSentenceMapper:
    def __init__(self, output_dir):
        self.output = open(output_dir, "w")
        self.output.write(f'Collocation_id\tSentence_id\n')

    def close(self):
        self.output.close()

    def add_map(self, collocation_id, sentence_id):
        """ Adds a new line to output. """
        self.output.write(f'{collocation_id}\t{sentence_id}\n')
