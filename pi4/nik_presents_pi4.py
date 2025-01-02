#!/usr/bin/python3

import sys
import random
import json
import argparse
import os
import threading

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
from gtk4_mpv import MyRenderer


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app, jsonfile, media_home, timeout, duration, verbose, *args, **kwargs):
        super().__init__(application=app, *args, **kwargs)

        # read in json track file
        with open(jsonfile, 'r') as jfile:
            data = jfile.read()

        self.tracks = json.loads(data)["tracks"]
        #shuffle the tracks so that they are random
        # random.shuffle(self.tracks)

        # set up CSS for styling widgets
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(sys.path[0] + "/" + "style.css")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # using CSS to set background color
        self.set_css_classes(['appbg'])

        self.box = None
        self.image = None
        self.renderer = None
        self.label = None
        self.track_number = -1
        self.verbose = verbose
        self.media_home = media_home
        self.duration = duration
        # can't use the window directly, have to use a canvas
        # to place widgets on. If you use the window directly,
        # you get openGL errors on a video to image transition.
        self.canvas = Gtk.Fixed()

        # set up key press 'q' for quitting
        evk_quit = Gtk.EventControllerKey.new()
        evk_quit.connect("key-pressed", self.key_press)
        self.add_controller(evk_quit)

        evk_mouse = Gtk.GestureClick.new()
        evk_mouse.connect("pressed", self.onClick)
        self.add_controller(evk_mouse)
        
        self.set_child(self.canvas)
        self.fullscreen()
        self.next_track()


    def key_press(self, event, keyval, keycode, state):
        # check if keypress is 'q'
        if keyval == Gdk.KEY_q:
            self.close()
            
    def onClick(self, gesture, data, x, y):
        if self.verbose:
            print("got click",x,y)


    def next_track(self):
        # if self.renderer:
        #     self.renderer._mpv.terminate()

        # increment the track number by 1
        # if at end of tracks, then shuffle tracks and
        # set track number to first track
        self.track_number += 1
        if self.track_number == len(self.tracks):
            random.shuffle(self.tracks)
            self.track_number = 0
            
        self.current_track = self.tracks[self.track_number]

        if self.verbose:
            print("playing track "+str(self.track_number)+": "+self.current_track['location'], flush=True)

        if (self.current_track["type"] == "image"):
            self.process_image()
        elif (self.current_track["type"] == "video"):
            self.play_video()

    def prev_track(self):
        
        # decrement the track number by 1
        # if at beginning of tracks, then set track number to last track
        self.track_number -= 1
        if self.track_number == -1:
            self.track_number = len(self.tracks)-1
            
        self.current_track = self.tracks[self.track_number]
        
        if self.verbose:
            print("playing track "+str(self.track_number)+": "+self.current_track['location'], flush=True)
        
        if (self.current_track["type"] == "image"):
            self.process_image()
        elif (self.current_track["type"] == "video"):
            self.play_video()

    def process_image(self):
        self.image = Gtk.Picture.new_for_filename(self.complete_path(self.current_track["location"]))

        # get the width and height of the image
        image_width = self.image.get_paintable().get_intrinsic_width()
        image_height = self.image.get_paintable().get_intrinsic_height()

        label_text = ""
        # if image is less than 1800 wide, then put text to left of image,
        # otherwise put it above image.
        if image_width < 1800:
            label_text = self.current_track["trip-text"] + "\n\n" + self.current_track["annot-text"]
            self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            self.box.set_css_classes(['appbg'])

            self.label = Gtk.Label(label=label_text)
            # set label size based on centering the image horizontally
            self.label.set_size_request((1920 - image_width) / 2, -1)

        else:
            label_text = self.current_track["trip-text"]
            if self.current_track["annot-text"]:
                label_text += " - " + self.current_track["annot-text"]
            self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.box.set_css_classes(['appbg'])

            self.label = Gtk.Label(label=label_text)
            # set label size based on centering the image vertically
            self.label.set_size_request(-1, (1080 - image_height) / 2)

        self.label.set_wrap(True)
        self.label.set_css_classes(['annot'])
        self.label.set_xalign(0)
        self.label.set_yalign(0)
        self.box.append(self.label)
        self.box.append(self.image)
        # have to set size request, otherwise you get nothing
        self.box.set_size_request(1920,1080)
        
        self.canvas.put(self.box,0,0)
        
        print("about to set timer")
        # set a timer for the duration of the image
        GLib.timeout_add_seconds(self.duration, self.next_track)


    def play_video(self):
        print("in play video")
        # if self.box:
            # self.canvas.remove(self.box)
        self.renderer = MyRenderer()
        self.renderer.connect("realize", self.on_renderer_ready)
        self.renderer._mpv.observe_property('eof-reached', self.handlePropertyChange)
        # have to set size request, otherwise you get nothing
        self.renderer.set_size_request(1920,1080)
        self.canvas.put(self.renderer,0,0)
        print("end of play video")


    def on_renderer_ready(self, *_):
        print("in renderer ready")
        self.renderer.play(self.complete_path(self.current_track['location']))


    def handlePropertyChange(self, name, value):
        if self.verbose:
            print('property change', name, value)

        # check to see if the video has ended
        if (name == 'eof-reached' and value == True):
            print('here')
            GLib.idle_add(self.next_track)

    def complete_path(self,track_file):
        #  complete path of the filename of the selected entry
        if track_file != '' and track_file[0]=="+":
            track_file=self.media_home+track_file[1:]
        return track_file
    


class MyApp(Gtk.Application):
    def __init__(self, jsonfile, mediadir, timeout, duration, verbose):
        super().__init__()
        self.jsonfile = jsonfile
        self.mediadir = mediadir
        self.timeout = timeout
        self.duration = duration
        self.verbose = verbose
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(app, self.jsonfile, self.mediadir, self.timeout, self.duration, self.verbose)
        self.win.present()


parser = argparse.ArgumentParser()
parser.add_argument("--jsonfile", help="JSON file with tracks.", required=True)
parser.add_argument("--mediadir", help="Root directory for media.", required=True)
parser.add_argument("--timeout", help="Number of seconds for PIR timeout (Default 120).", default=120, type=int)
parser.add_argument("--duration", help="Number of seconds images are shown (Default 8).", default=8, type=int)
parser.add_argument("--verbose", help="Informational output to STDOUT.", default=False, action='store_true')
args = parser.parse_args()

if (not os.path.exists(args.jsonfile)):
    print("Error: JSON file '"+args.jsonfile+"' not found.", file=sys.stdout)
    sys.exit(1)

if (not os.path.isfile(args.jsonfile)):
    print("Error: Path '"+args.jsonfile+"' is not a file.", file=sys.stdout)
    sys.exit(1)
    
if (not os.path.exists(args.mediadir)):
    print("Error: Media directory '"+args.mediadir+"' does not exist.", file=sys.stdout)
    sys.exit(1)
    
if (not os.path.isdir(args.mediadir)):
    print("Error: Media directory path '"+args.mediadir+"' is not a directory.", file=sys.stdout)
    sys.exit(1)

app = MyApp(args.jsonfile, args.mediadir, args.timeout, args.duration, args.verbose)
app.run()
