"""
Class for estimating remaining calculation time. Works only for multiple files input.
"""
from datetime import timedelta, datetime
import logging


class TimeInfo:
    def __init__(self, to_go):
        self.times = []
        self.to_go = to_go

    def add_measurement(self, time_measurement):
        """ Adds measurement to times for a better calculation. """
        if time_measurement > 0:
            self.times.append(time_measurement)
        self.to_go -= 1

    def info(self):
        """ Logs remaining time estimation. """
        seconds = sum(self.times) / len(self.times)
        td = timedelta(seconds=int(seconds * self.to_go))
        ft = datetime.now() + td
        logging.info("Going to finish in {}".format(ft.strftime("%d/%m @ %H:%M")))
