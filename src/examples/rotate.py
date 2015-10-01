""" Rotating LED pattern """
from myhdl import *

def top(pins):
    counter = Signal(intbv(0, min=0, max=2000000))
    rotator = Signal(intbv(0)[4:])

    @always(pins.clk.posedge)
    def rotate():
        """ Rotate every time counter reaches max """
        if counter == counter.max - 1:
            rotator.next = concat(rotator[3:], rotator[3])
            counter.next = 0
        else:
            counter.next = counter + 1

        # set initial bits
        if rotator == 0:
            rotator.next = 1

    @always_comb
    def drive_leds():
        """ drive each LED if the bit equals one """
        pins.D4.next = rotator[3] == 1
        pins.D3.next = rotator[2] == 1
        pins.D2.next = rotator[1] == 1
        pins.D1.next = rotator[0] == 1

    return instances()
