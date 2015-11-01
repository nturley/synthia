""" Blinks an LED """
from myhdl import *

def top(pins):
    counter = Signal(modbv(0)[23:])
    half_max = counter.max // 2

    @always(pins.clk.posedge)
    def count():
        """ Increments counter every time the clock rises """
        counter.next = counter + 1

    @always_comb
    def drive_led():
        """ Drive LED when counter is more than half way to max """
        if counter > half_max:
            pins.D5.next = True
        else:
            pins.D5.next = False

    return instances()