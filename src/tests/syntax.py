""" Blinks an LED """
from myhdl import *

def top(pins):

    @always(pins.clk.posedge)
    def count():
        """ Increments counter every time the clock rises """
        bob.next = 1

    return instances()
