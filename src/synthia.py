from gi.repository import Gtk, GtkSource, GObject, Pango
from os.path import abspath, dirname, join

import subprocess

import verilogifier
from myhdl import ConversionError

UI_PATH = join(abspath(dirname(__file__)), 'ui.glade')
PCF_PATH = join(abspath(dirname(__file__)), 'top.pcf')


class Synthia(object):
    def __init__(self):
        self.docPath = None
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
        self.docPath = None
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
            self.docPath = dialog.get_filename()
            with open(self.docPath) as f:
                self.sourceBuffer.set_text(f.read())
        dialog.destroy()

    def saveasBtn_click(self, button):
        fname = self.savedialog()
        if fname is None:
            return
        self.docPath = fname
        self.saveFile()

    def saveBtn_click(self, button):
        if self.docPath is not None:
            self.saveFile()
        else:
            self.saveAsBtn_click(button)

    def saveFile(self):
        startiter = self.sourceBuffer.get_start_iter()
        enditer = self.sourceBuffer.get_end_iter()
        text = self.sourceBuffer.get_text(startiter,enditer, False)
        with open(self.docPath, 'w') as f:
            f.write(text)

    def savedialog(self):
        dialog = Gtk.FileChooserDialog("Save file as...",
                                       self.window,
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_SAVE,
                                        Gtk.ResponseType.OK))
        filter_py = Gtk.FileFilter()
        filter_py.set_name("Python files")
        filter_py.add_mime_type("text/x-python")
        dialog.add_filter(filter_py)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            fname = dialog.get_filename()
        else:
            fname = None
        dialog.destroy()
        return fname

    def compile_click(self, button):
        self.saveBtn_click(button)
        if self.docPath is None:
            return
        # write the verilog version to /tmp/top.v
        print('myHDL...')
        print('***************************************')
        try:
            verilogifier.verilogify(self.docPath)
        except ConversionError as e:
            dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK, "MyHDL Error")
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
        except verilogifier.NoTopException as e:
            dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK, "Synthia Error")
            dialog.format_secondary_text('Compiled file must have a "top" function')
            dialog.run()
            dialog.destroy()
        print('********************************************')
        print('yosys...')
        print('********************************************')

        subprocess.call('yosys -q -p "synth_ice40 -blif /tmp/top.blif" /tmp/top.v', shell=True)
        print('********************************************')
        print('arachne-pnr...')
        print('********************************************')
        subprocess.call('arachne-pnr -p ' + PCF_PATH + ' /tmp/top.blif -o /tmp/top.txt', shell=True)
        print('********************************************')
        print('icepack...')
        print('********************************************')
        subprocess.call(['icepack', '/tmp/top.txt', '/tmp/top.bin'])
        print('********************************************')
        print('compile complete')
    def deploy_click(self, button):
        print('compile...')
        self.compile_click(button)
        print('deploy...')
        subprocess.call(['/usr/local/bin/iceprog', '/home/nturley/synthia/top.bin'])
        print('deploy complete')

if __name__ == '__main__':
    gui = Synthia()
    Gtk.main()
