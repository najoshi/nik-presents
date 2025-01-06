#!/usr/bin/python3

import sys
import random
import json
import argparse
import os
import time
import subprocess

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib

from gpiozero import MotionSensor
from gtk4_mpv import MPVRenderer


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app, jsonfile, media_home, timeout, duration, verbose, *args, **kwargs):
        super().__init__(application=app, *args, **kwargs)

        # read in json track file
        with open(jsonfile, 'r') as jfile:
            data = jfile.read()

        self.tracks = json.loads(data)["tracks"]
        #shuffle the tracks so that they are random
        random.shuffle(self.tracks)

        # set up CSS for styling widgets
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(sys.path[0] + "/" + "style.css")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # using CSS to set background color
        self.set_css_classes(['appbg'])

        self.box = None
        self.box2 = None
        self.image = None
        self.renderer = None
        self.label = None
        self.pause_label = None
        self.glib_timer = None
        self.timer_active = False
        self.running = True
        self.paused = False
        self.track_number = -1
        self.current_track = None
        self.verbose = verbose
        self.media_home = media_home
        self.duration = duration
        self.timeout = timeout
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
        
        # set up motion sensor
        self.pir = MotionSensor(23)
        self.pir.when_motion = self.do_motion
        self.last_motion_time = time.time()
        # call check_timeout every 100 milliseconds
        GLib.timeout_add(100, self.check_timeout)
        
        self.set_child(self.canvas)
        self.fullscreen()
        self.next_track()


    def check_timeout(self):
        # if the current time is greater than the last time there was motion
        # plus the timeout, then turn off the monitor and pause
        if (self.running and (time.time() > (self.last_motion_time + self.timeout))):
            if self.verbose: print("timeout reached, turning off", flush=True)
            self.running = False
            self.pause_on()
            self.turn_off_monitor()
        return True
        
    def do_motion(self):
        if self.verbose: print("detected motion", flush=True)
        self.last_motion_time = time.time()
        if (not self.running):
            self.running = True
            self.turn_on_monitor()
            self.pause_off()
            self.fullscreen()

    def key_press(self, event, keyval, keycode, state):
        # check if keypress is 'q'
        if keyval == Gdk.KEY_q:
            if self.verbose: print("quitting")
            self.close()
            
            
    def onClick(self, gesture, data, x, y):
        if self.verbose:
            print("got click",x,y)
            
        if (x<640):
            # touching first third of screen goes to previous track, unless
            # track is video and touch is in lower left corner,
            # then goes back 10 seconds.
            if (self.current_track["type"] == "video" and x<100 and y>980):
                if self.verbose: print ("skipping back 10 secs", flush=True)
                self.renderer._mpv.seek(-10, reference="relative")
            else:
                if self.verbose: print ("going to previous track", flush=True)
                GLib.idle_add(self.prev_track)
                
        elif (x>=640 and x<1280):
            # touching middle third of screen pauses track
            if (self.paused):
                self.pause_off()
            else:
                self.pause_on()
                
        elif (x>=1280):
            # touching last third of screen goes to next track
            # unless track is video and touch is in upper right corner,
            # then toggles mute. If track is video and touch is in lower 
            # right, then it skips forward 10 seconds.
            if (self.current_track["type"] == "video" and x>1820 and y<100):
                if (self.renderer._mpv.mute):
                    if self.verbose: print("Unmuting...")
                    self.renderer._mpv.mute = False
                else:
                    if self.verbose: print("Muting...")
                    self.renderer._mpv.mute = True
                    
            elif (self.current_track["type"] == "video" and x>1820 and y>980):
                if self.verbose: print ("skipping forward 10 secs", flush=True)
                self.renderer._mpv.seek(10, reference="relative")
                
            else:
                if self.verbose: print ("going to next track", flush=True)
                GLib.idle_add(self.next_track)
       
                
    def turn_on_monitor(self):
        subprocess.call("ddcutil setvcp D6 04", shell=True)
        #subprocess.call("wlr-randr --output HDMI-A-1 --on", shell=True)
        
    def turn_off_monitor(self):
        subprocess.call("ddcutil setvcp D6 05", shell=True)
        #subprocess.call("wlr-randr --output HDMI-A-1 --off", shell=True)


    def next_track(self):
        # turn off pause if necessary
        self.pause_off()
        
        # cancel the image timer
        if self.glib_timer and self.timer_active:
            GLib.source_remove(self.glib_timer)
            self.timer_active = False
        
        # terminate the video
        if self.renderer:
            # when video is stopped, the "eof-property" is changed to True
            # which then activates the handlePropertyChange callback
            self.renderer._mpv.command("stop")
        
        # increment the track number by 1
        # if at end of tracks, then shuffle tracks and
        # set track number to 0
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
        # turn off pause if necessary
        self.pause_off()
        
        # cancel the image timer
        if self.glib_timer and self.timer_active:
            GLib.source_remove(self.glib_timer)
            self.timer_active = False
        
        # terminate the video
        if self.renderer:
            self.renderer._mpv.command("stop")
        
        # decrement the track number by 1
        # if at beginning of tracks, then set track number to 0
        self.track_number -= 1
        if self.track_number == -1:
            self.track_number = 0
            
        self.current_track = self.tracks[self.track_number]
        
        if self.verbose:
            print("playing track "+str(self.track_number)+": "+self.current_track['location'], flush=True)
        
        if (self.current_track["type"] == "image"):
            self.process_image()
        elif (self.current_track["type"] == "video"):
            self.play_video()


    def pause_on(self):
        # if already paused, then don't need to do anything
        if (self.paused):
            return
            
        if self.verbose: print ("turning on pause", flush=True)
        self.paused = True
        
        if (self.current_track["type"] == "image"):
            # cancel the image timer
            if self.glib_timer:
                GLib.source_remove(self.glib_timer)
                self.timer_active = False
            self.pause_label.set_text("Paused...")
            
        elif (self.current_track["type"] == "video"):
            # pause the video and show "Paused..." text
            # with a long duration so it doesn't disappear
            self.renderer._mpv.pause = True
            self.renderer._mpv.command("show_text", "Paused...", 100000)
            
    def pause_off(self):
        # if already unpaused, then don't need to do anything
        if (not self.paused):
            return
            
        if self.verbose: print ("turning off pause", flush=True)
        self.paused = False
        
        if (self.current_track["type"] == "image"):
            self.pause_label.set_text("")
            self.glib_timer = GLib.timeout_add_seconds(self.duration, self.next_track)
            self.timer_active = True
            
        elif (self.current_track["type"] == "video"):
            # unpause the video and remove the "Paused..." text
            self.renderer._mpv.pause = False
            self.renderer._mpv.command("show_text", "")


    def process_image(self):
        
        image_path = self.complete_path(self.current_track["location"])

        if (not os.path.exists(image_path)):
            print("image not found:",image_path)

        self.image = Gtk.Picture.new_for_filename(image_path)

        # get the width and height of the image
        image_width = self.image.get_paintable().get_intrinsic_width()
        image_height = self.image.get_paintable().get_intrinsic_height()

        label_text = ""
        # if image is less than 1800 wide, then put text to left of image,
        # otherwise put it above image.
        if image_width < 1800:
            label_text = self.current_track["trip-text"] + "\n\n" + self.current_track["annot-text"]
            self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            self.box2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.box.set_css_classes(['appbg'])

            self.label = Gtk.Label(label=label_text)
            # set label size based on centering the image horizontally
            self.label.set_size_request((1920 - image_width) / 2, -1)
            self.label.set_vexpand(True)

        else:
            label_text = self.current_track["trip-text"]
            if self.current_track["annot-text"]:
                label_text += " - " + self.current_track["annot-text"]
            self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            self.box.set_css_classes(['appbg'])

            self.label = Gtk.Label(label=label_text)
            # set label size based on centering the image vertically
            self.label.set_size_request(-1, (1080 - image_height) / 2)
            self.label.set_hexpand(True)

        self.label.set_wrap(True)
        self.label.set_css_classes(['annot'])
        self.label.set_xalign(0)
        self.label.set_yalign(0)
        self.label.set_margin_end(10)
        
        self.pause_label = Gtk.Label()
        self.pause_label.set_css_classes(['annot'])
        self.pause_label.set_xalign(0)
        self.pause_label.set_yalign(0)
        self.pause_label.set_size_request(100,50)
        
        self.box2.set_css_classes(['appbg'])
        self.box2.append(self.label)
        self.box2.append(self.pause_label)
        
        self.box.append(self.box2)
        self.box.append(self.image)
        # have to set size request, otherwise you get nothing
        self.box.set_size_request(1920,1080)
        
        self.canvas.put(self.box,0,0)
        
        # set a timer for the duration of the image
        self.glib_timer = GLib.timeout_add_seconds(self.duration, self.next_track)
        self.timer_active = True


    def play_video(self):        
        if self.verbose:
            print ("playing video "+self.current_track['location'], flush=True)
        
        # need to escape ":" because it is special character for mpv subtitles list
        # instantiate MPVRenderer and set subtitle path
        self.renderer = MPVRenderer(subfile=self.complete_path(self.current_track['subtitles-file']).replace(":","\\:"))
            
        self.renderer.connect("realize", self.on_renderer_ready)
        # checking for "eof-reached" when video finishes
        self.renderer._mpv.observe_property('eof-reached', self.handlePropertyChange)
        # have to set size request, otherwise you get nothing
        self.renderer.set_size_request(1920,1080)
        self.canvas.put(self.renderer,0,0)


    def on_renderer_ready(self, *_):
        video_path = self.complete_path(self.current_track['location'])
        if (not os.path.exists(video_path)):
            print("image not found:",video_path)
        self.renderer.play(video_path)


    def handlePropertyChange(self, name, value):
        if self.verbose:
            print('property change', name, value)

        # check to see if the video has ended
        if (name == 'eof-reached' and value == True):
            # go to next track
            GLib.idle_add(self.next_track)

    def complete_path(self,track_file):
        #  complete path of the filename of the selected entry
        if track_file != '' and track_file[0]=="+":
            track_file=self.media_home+track_file[1:]
        return track_file
    


class DMFApp(Gtk.Application):
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

app = DMFApp(args.jsonfile, args.mediadir, args.timeout, args.duration, args.verbose)
app.run()
