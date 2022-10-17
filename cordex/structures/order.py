"""
A file that takes care of order of children in structures.
"""
from enum import Enum


class Order(Enum):
    FromTo = 0
    ToFrom = 1
    Any = 2

    @staticmethod
    def new(order):
        """ Creates a new order. """
        if order is None:
            return Order.Any
        elif order == "to-from":
            return Order.ToFrom
        elif order == "from-to":
            return Order.FromTo
        else:
            raise NotImplementedError("What kind of ordering is: {}".format(order))

    def match(self, from_w, to_w):
        """ Checks whether word order is correct. """
        if self is Order.Any:
            return True

        fi = from_w.int_id
        ti = to_w.int_id

        if self is Order.FromTo:
            return fi < ti
        elif self is Order.ToFrom:
            return ti < fi
        else:
            raise NotImplementedError("Should not be here: Order match")
