from gi.repository import Gtk, GtkSource, GObject, Pango
from os.path import abspath, dirname, join

import subprocess

UI_PATH = join(abspath(dirname(__file__)), 'ui.glade')

class Synthia(object):
    def __init__(self):
        builder = Gtk.Builder()
        GObject.type_register(GtkSource.View)
        builder.add_from_file(UI_PATH)
        self.window = builder.get_object("window1")
        view = builder.get_object("gtksourceview1")
        handlers = {
            "on_compile_clicked": self.compile_click,
            "on_deploy_clicked": self.deploy_click,
            "on_newBtn_activate": self.newBtn_click,
            "on_openBtn_activate": self.openBtn_click,
            "on_saveasBtn_activate" : self.saveasBtn_click,
            "on_saveBtn_activate" : self.saveBtn_click,
            "quit" : Gtk.main_quit
        }
        builder.connect_signals(handlers)
        lang = GtkSource.LanguageManager.get_default().get_language('python')
        self.sourceBuffer = GtkSource.Buffer.new_with_language(lang)
        font_desc = Pango.FontDescription('monospace 10')
        if font_desc:
            view.modify_font(font_desc)
        view.set_buffer(self.sourceBuffer)
        if (self.window):
            self.window.connect("destroy", Gtk.main_quit)
            self.window.set_size_request(600, 650)

    def newBtn_click(self, button):
        self.sourceBuffer.set_text('from myhdl import *\n\ndef top(pins):\n    \n    return instances()')

    def openBtn_click(self, button):
        dialog = Gtk.FileChooserDialog("Please choose a file", self.window,
                Gtk.FileChooserAction.OPEN,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        filter_py = Gtk.FileFilter()
        filter_py.set_name("Python files")
        filter_py.add_mime_type("text/x-python")
        dialog.add_filter(filter_py)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            with open(dialog.get_filename()) as f:
                self.sourceBuffer.set_text(f.read())
        dialog.destroy()

    def saveasBtn_click(self, button):
        print('save as')

    def saveBtn_click(self, button):
        print('save')

    def compile_click(self, button):
        print('Compile!')
        startiter = self.sourceBuffer.get_start_iter()
        enditer = self.sourceBuffer.get_end_iter()
        text = self.sourceBuffer.get_text(startiter,enditer, False)

        import os
        for fname in ['./top.py', './top.v', './top.blif', './top.txt', './top.bin']:
            try:
                print('delete '+fname)
                os.remove(fname)
            except OSError, e:
                print(e.strerror)

        f = open('./top.py', 'w')
        f.write(text)
        f.close()
        print('file written')

        from myhdl import Signal, toVerilog

        class IceStick:
            def __init__(self):
                self.D1, self.D2, self.D3, self.D4, self.D5 = [Signal(bool(0)) for i in range(5)]
                self.clk = Signal(bool(0))

        pins = IceStick()
        print('********************************************')
        print('toVerilog...')
        import top
        reload (top)
        toVerilog(top.top, pins)
        del top
        print('********************************************')
        print('yosys...')
        print('********************************************')

        subprocess.call('yosys -q -p "synth_ice40 -blif top.blif" top.v', shell=True)

        print('********************************************')
        print('arachne-pnr...')
        print('********************************************')
        subprocess.call('arachne-pnr -p top.pcf top.blif -o top.txt', shell=True)
        print('********************************************')
        print('icepack...')
        print('********************************************')
        subprocess.call(['/usr/local/bin/icepack', '/home/nturley/synthia/top.txt', '/home/nturley/synthia/top.bin'])
        print('********************************************')
        print('compile complete')
        print('********************************************')

    def deploy_click(self, button):
        print('compile...')
        self.compile_click(button)
        print('deploy...')
        subprocess.call(['/usr/local/bin/iceprog', '/home/nturley/synthia/top.bin'])
        print('deploy complete')

if __name__ == '__main__':
    gui = Synthia()
    Gtk.main()
