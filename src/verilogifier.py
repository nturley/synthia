import imp
from myhdl import Signal, toVerilog
import os.path

class NoTopException(Exception):
	pass

class IceStick:
    def __init__(self):
        self.D1, self.D2, self.D3, self.D4, self.D5 = [Signal(bool(0)) for i in range(5)]
        self.clk = Signal(bool(0))

def verilogify(fname):
	pins = IceStick()
	mod = imp.load_source('top', fname)
	try:
		mytop = mod.top
	except AttributeError as e:
		raise NoTopException
	toVerilog.name = 'top'
	toVerilog.directory = '/tmp/'
	toVerilog(mytop, pins)