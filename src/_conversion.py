""" Helper for myHDL conversion """
import imp
import os
import subprocess
import sys
import traceback

from myhdl import ConversionError, Signal, toVerilog

WORKING_DIR = os.path.abspath(os.path.dirname(__file__))
ERROR_LOG_FILE = os.path.join(WORKING_DIR, "_verilogify_errors.log")


class NoTopException(Exception):
    pass


class IceStick:
    def __init__(self):
        self.D1, self.D2, self.D3, self.D4, self.D5 = [Signal(bool(0)) for _ in range(5)]
        self.clk = Signal(bool(0))


def verilogify(fname):
    # Because the Python import machinery (apparently) does not correctly
    # update modified local functions inside the `top` function when the user's
    # script is reimported, launch a child process to do a from-scratch import
    # and Verilog conversion every time. The child process is launched using
    # the same version of Python, using the directory containing this script
    # (_conversion.py) as the working path, and the path to the user's module
    # as the first argument.
    script_path = os.path.abspath(__file__)
    module_path = os.path.abspath(fname)
    print "running %s %s %s" % (sys.executable, script_path, module_path)
    result = subprocess.call([sys.executable, script_path, module_path])
    if 1 == result:
        raise NoTopException
    elif 2 == result:
        raise ConversionError(read_error())
    elif 0 != result:
        raise Exception(read_error())


def create_verilog(fname):
    pins = IceStick()

    with open(fname, 'r') as f:
        mod = imp.load_module('top', f, fname, ('.py', 'r', imp.PY_SOURCE))
        if not hasattr(mod, 'top'):
            raise NoTopException

        toVerilog.name = 'top'
        toVerilog.directory = '/tmp/'
        toVerilog(mod.top, pins)


def read_error():
    with open(ERROR_LOG_FILE) as f:
        return f.read()


def write_error(msg):
    with open(ERROR_LOG_FILE, 'w') as f:
        f.write(msg)


if __name__ == '__main__':
    # When this script is executed directly, it is assumed that there is one
    # argument, the path to the user script to be converted to Verilog.
    if os.path.isfile(ERROR_LOG_FILE):
        os.unlink(ERROR_LOG_FILE)

    try:
        create_verilog(sys.argv[1])
    except NoTopException:
        traceback.print_exc()
        sys.exit(1)
    except ConversionError:
        traceback.print_exc()
        write_error(traceback.format_exc())
        sys.exit(2)
    except:
        traceback.print_exc()
        write_error(traceback.format_exc())
        sys.exit(-1)

    sys.exit(0)
