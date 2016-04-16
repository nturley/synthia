""" Main module for synthia application """
# gtk
from gi.repository import Gtk, GtkSource, GObject, Pango, GLib, Gdk

# standard libs
from os.path import abspath, dirname, join
import subprocess
import Queue

# myHDL
from myhdl import ConversionError

# synthesis tools
import _conversion


UI_PATH = join(abspath(dirname(__file__)), 'ui.glade')
PCF_PATH = join(abspath(dirname(__file__)), 'top.pcf')
DEFAULT_TEXT = '''from myhdl import *

def top(pins):
    # your logic goes here

    return instances()'''


class Synthia(object):
    """ The main application class """
    def __init__(self):
        self.docpath = None
        self.message_q = Queue.Queue()
        GLib.idle_add(self.on_idle)

        builder = Gtk.Builder()
        GObject.type_register(GtkSource.View)
        builder.add_from_file(UI_PATH)
        self.window = builder.get_object("window1")
        self.statusbar = builder.get_object("statusbar1")
        self.statuscontext = self.statusbar.get_context_id("info")
        view = builder.get_object("gtksourceview1")
        handlers = {
            "on_compile_clicked": self.compileclicked,
            "on_deploy_clicked": self.deployclicked,
            "on_newBtn_activate": self.newbuttonclicked,
            "on_openBtn_activate": self.openbuttonclicked,
            "on_saveasBtn_activate" : self.saveasbuttonclicked,
            "on_saveBtn_activate" : self.savebuttonclicked,
            "on_cutBtn_activate" : self.cutbuttonclicked,
            "on_copyBtn_activate" : self.copybuttonclicked,
            "on_pasteBtn_activate" : self.pastebuttonclicked,
            "quit" : Gtk.main_quit
        }
        builder.connect_signals(handlers)
        lang = GtkSource.LanguageManager.get_default().get_language('python')
        self.sourcebuffer = GtkSource.Buffer.new_with_language(lang)
        font_desc = Pango.FontDescription('monospace 10')
        if font_desc:
            view.modify_font(font_desc)
        view.set_buffer(self.sourcebuffer)
        if self.window:
            self.window.connect("destroy", Gtk.main_quit)
            self.window.set_size_request(600, 650)
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

    def on_idle(self):
        """Check for new messages and update the status bar."""
        try:
            message = self.message_q.get(block=False)
            self.statusbar.push(self.statuscontext, message)
        except Queue.Empty:
            pass

        return True

    def newbuttonclicked(self, _):
        """ resets docpath and sets the text to the default text """
        self.docpath = None
        self.sourcebuffer.set_text(DEFAULT_TEXT)

    def openbuttonclicked(self, _):
        """ Opens a file chooser dialog,
        sets docpath, and pushes it into the source buffer """
        dialog = Gtk.FileChooserDialog("Please choose a file",
                                       self.window,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN,
                                        Gtk.ResponseType.OK))

        filter_py = Gtk.FileFilter()
        filter_py.set_name("Python files")
        filter_py.add_mime_type("text/x-python")
        dialog.add_filter(filter_py)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.docpath = dialog.get_filename()
            with open(self.docpath) as source_file:
                self.sourcebuffer.set_text(source_file.read())
        dialog.destroy()

    def saveasbuttonclicked(self, _):
        """ opens up file chooser dialog,
        sets docpath, and saves to disk """
        fname = self.savedialog()
        if fname is None:
            return
        self.docpath = fname
        self.savefile()

    def savebuttonclicked(self, _):
        """ if docpath isn't set, does a saveas,
        otherwise, just saves the file """
        if self.docpath is not None:
            self.savefile()
        else:
            self.saveasbuttonclicked(None)

    def cutbuttonclicked(self, _):
        self.sourcebuffer.cut_clipboard(self.clipboard, True)

    def copybuttonclicked(self, _):
        self.sourcebuffer.copy_clipboard(self.clipboard)

    def pastebuttonclicked(self, _):
        self.sourcebuffer.paste_clipboard(self.clipboard, None, True)

    def savefile(self):
        """ saves the text in the sourcebuffer to docPath """
        startiter = self.sourcebuffer.get_start_iter()
        enditer = self.sourcebuffer.get_end_iter()
        text = self.sourcebuffer.get_text(startiter, enditer, False)
        with open(self.docpath, 'w') as destination_file:
            destination_file.write(text)

    def savedialog(self):
        """ opens a save file chooser
        returns selected file path or None if canceled """
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

    def compileclicked(self, _):
        """ saves file and kicks off the verification pass """
        self.savebuttonclicked(None)
        if self.docpath is None:
            return
        self.check()

    def deployclicked(self, _):
        """ saves file and kicks off verification, synthesis, and deployment pass """
        self.savebuttonclicked(None)
        if self.docpath is None:
            return
        self.deploy()

    def deploy(self):
        """ Calls myHDL, Yoysys, Arachne-pnr, icepack, and iceprog
        to generate a bitstream and deploy it to the icestick """
        self.message_q.put('Analyzing...')
        # write the verilog version to /tmp/top.v
        print 'myHDL...'
        print '***************************************'
        if not self.converttoverilog():
            self.message_q.put('Verify failed!  Deployment aborted.')
            return

        self.message_q.put("Synthesizing...")
        print '********************************************'
        print 'yosys...'
        print '********************************************'
        subprocess.call('yosys -q -p "synth_ice40 -blif /tmp/top.blif" /tmp/top.v', shell=True)
        print '********************************************'
        
        self.message_q.put("Placing and Routing...")
        print 'arachne-pnr...'
        print '********************************************'
        subprocess.call('arachne-pnr -p ' + PCF_PATH + ' /tmp/top.blif -o /tmp/top.txt', shell=True)
        print '********************************************'
        self.message_q.put("Generating bitfile...")
        print 'icepack...'
        print '********************************************'
        subprocess.call('icepack /tmp/top.txt /tmp/top.bin', shell=True)
        print '********************************************'
        self.message_q.put("Deploying bitfile...")
        print 'deploy...'
        subprocess.call('iceprog /tmp/top.bin', shell=True)
        self.message_q.put("Bitfile deployed")
        print 'deploy complete'

    def check(self):
        """ checks to see if it can convert to verilog and if it has a "top" """
        self.message_q.put("Verifying...")
        if self.converttoverilog():
            self.message_q.put("Verify complete")
        else:
            self.message_q.put("Verify failed!")

    def converttoverilog(self):
        """ runs myHDL verilog conversion """
        print 'myHDL...'
        print '***************************************'
        try:
            _conversion.verilogify(self.docpath)
        except ConversionError as error:
            dialog = Gtk.MessageDialog(self.window,
                                       0,
                                       Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.OK,
                                       "MyHDL Error")
            dialog.format_secondary_text(str(error))
            dialog.run()
            dialog.destroy()
            return False
        except _conversion.NoTopException:
            dialog = Gtk.MessageDialog(self.window,
                                       0,
                                       Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.OK,
                                       "Synthia Error")
            dialog.format_secondary_text('Compiled file must have a "top" function')
            dialog.run()
            dialog.destroy()
            return False

        return True

if __name__ == '__main__':
    gui = Synthia()
    Gtk.main()
