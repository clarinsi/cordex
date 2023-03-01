"""
Tools for handling memory/actual database.
"""
import sqlite3
import os


class Database:
    def __init__(self, args):
        filename = ":memory:" if args['db'] is None else args['db']

        if args['overwrite_db'] and os.path.exists(filename):
            os.remove(filename)

        self.new = not os.path.exists(filename)
        self.db = sqlite3.connect(filename)

        self.init("CREATE TABLE StepsDone ( step varchar(32) )")
        self.commit()
    
    def execute(self, *args, **kwargs):
        """ Executes database command.  """
        return self.db.execute(*args, **kwargs)

    def init(self, *args, **kwargs):
        """ Same as execute, only skipped if not a new database file. """
        if self.new:
            return self.execute(*args, **kwargs)
    
    def commit(self):
        """ Commits changes. """
        self.db.commit()

    def is_step_done(self, step_name):
        """ Checks whether step results are in database. """
        wc_done = self.db.execute("SELECT count(*) FROM StepsDone WHERE step=?", (step_name, )).fetchone()
        return wc_done[0] != 0

    def step_is_done(self, step_name):
        """ Completes and stores step. """
        self.db.execute("INSERT INTO StepsDone (step) VALUES (?)", (step_name, ))
        self.db.commit()

