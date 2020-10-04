#!/usr/bin/python3

from tkinter import *
from PIL import ImageTk,Image
import json
import sys
import textwrap
from gpiozero import MotionSensor
import time
import subprocess
import random
import argparse
import os
from pp_omxdriver import OMXDriver


class MainWindow():

    def __init__(self, main, jsonfile, media_home, timeout, duration, verbose):

        self.media_home = media_home
        self.main=main
        self.main.attributes("-fullscreen", True)
        self.main.bind("q", self.quit)

        with open(jsonfile, 'r') as jfile:
            data = jfile.read()

        self.tracks = json.loads(data)["tracks"]
        #shuffle the tracks so that they are random
        random.shuffle(self.tracks)

        # canvas for image
        self.canvas = Canvas(main, width = 1920, height = 1080, bg = "black", highlightthickness=0)
        self.canvas.pack()
        self.track_number = -1
        # create blank image to begin with
        self.image_on_canvas = self.canvas.create_image(960, 540, anchor = CENTER, image='')
        self.canvas.bind('<Button-1>',self.onClick)

        self.omx=None
        self.verbose = verbose
        self.image_timer=None
        self.video_timer=None
        self.annot=None
        self.img=None
        self.paused = False
        self.pause_text=None
        self.current_track=None
        self.running = True
        self.rect=None
        self.timeout = timeout
        self.duration = 1000 * duration
        self.pir = MotionSensor(17) # GPIO17 is pin 11
        self.last_motion_time = time.time()
        
        self.pir.when_motion = self.do_motion
        self.main.after(1,self.check_timeout)
        self.next_track()
        
    def check_timeout(self):
        # if the current time is greater than the last time there was motion
        # plus the timeout, then turn off the monitor and pause
        if (self.running and (time.time() > (self.last_motion_time + self.timeout))):
            if self.verbose: print("timeout reached, turning off", flush=True)
            self.running = False
            self.pause_on()
            self.turn_off_monitor()
        self.main.after(100,self.check_timeout)
        
    def do_motion(self):
        if self.verbose: print("detected motion", flush=True)
        self.last_motion_time = time.time()
        if (not self.running):
            self.running = True
            self.pause_off()
            self.turn_on_monitor()
            
    def turn_on_monitor(self):
        subprocess.call("vcgencmd display_power 1 > /dev/null", shell=True)
        
    def turn_off_monitor(self):
        subprocess.call("vcgencmd display_power 0 > /dev/null", shell=True)

    def onClick(self,event):
        x=event.x
        y=event.y
        if self.verbose: print ("screen click, "+self.current_track["type"]+" track, X value: "+str(x), flush=True)
        if (x<640):
            # touching first third of screen goes to previous track
            if self.verbose: print ("going to previous track", flush=True)
            self.prev_track()
        elif (x>=640 and x<1280):
            # touching middle third of screen pauses track
            if (self.paused):
                if self.verbose: print ("turning off pause", flush=True)
                self.pause_off()
            else:
                if self.verbose: print ("turning on pause", flush=True)
                self.pause_on()
        elif (x>=1280):
            # touching last third of screen goes to next track
            # unless track is video and touch is in upper right corner,
            # then toggles mute
            if (self.current_track["type"] == "video" and x>1820 and y<100):
                if (self.omx.muted):
                    if self.verbose: print("Unmuting...")
                    self.omx.unmute()
                else:
                    if self.verbose: print("Muting...")
                    self.omx.mute()
            else:
                if self.verbose: print ("going to next track", flush=True)
                self.next_track()

    def pause_on(self):
        # if already paused, then don't need to do anything
        if (self.paused):
            return
        
        self.paused = True
        
        if (self.current_track["type"] == "image"):
            self.main.after_cancel(self.image_timer)
            self.pause_text = self.canvas.create_text(1,1000,text="Paused...",anchor=NW,
                                                      fill="white",font=("Helvetica",20,"bold"))
            
        elif (self.current_track["type"] == "video"):
            self.omx.pause_on()
            
    def pause_off(self):
        # if already unpaused, then don't need to do anything
        if (not self.paused):
            return
        
        self.paused = False
        
        if (self.current_track["type"] == "image"):
            self.canvas.delete(self.pause_text)
            self.image_timer = self.main.after(self.duration, self.next_track)
            
        elif (self.current_track["type"] == "video"):
            self.omx.pause_off()


    def prev_track(self):
        self.pause_off()
        
        if (self.image_timer):
            self.main.after_cancel(self.image_timer)
        if (self.video_timer):
            self.main.after_cancel(self.video_timer)

        if (self.current_track["type"] == "video"):
            self.omx.terminate("prev track pressed")
        
        # decrement the track number by 1
        # if at beginning of tracks, then set track number to last track
        self.track_number -= 1
        if self.track_number == -1:
            self.track_number = len(self.tracks)-1
            
        self.current_track = self.tracks[self.track_number]
        
        if self.verbose:
            print("playing track "+str(self.track_number)+": "+self.current_track['location'], flush=True)
        
        if (self.current_track["type"] == "image"):
            self.update_image()
        elif (self.current_track["type"] == "video"):
            self.play_video()

    def next_track(self):
        self.pause_off()
        
        if (self.image_timer):
            self.main.after_cancel(self.image_timer)
        if (self.video_timer):
            self.main.after_cancel(self.video_timer)
            
        if (self.current_track and self.current_track["type"] == "video"):
            self.omx.terminate("next track pressed")
        
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
            self.update_image()
        elif (self.current_track["type"] == "video"):
            self.play_video()

    def check_video_loop(self):
        if (not self.omx.is_running()):
            if self.verbose: print("Video ended state seen")
            self.omx.kill()
            self.main.after_cancel(self.video_timer)
            self.next_track()
        else:
            self.video_timer = self.main.after(100,self.check_video_loop)
            
    def play_video(self):
        if (self.image_timer):
            self.main.after_cancel(self.image_timer)
        
        # remove image from canvas if exists
        if (self.annot):
            self.canvas.delete(self.annot)
        if (self.img):
            self.canvas.itemconfig(self.image_on_canvas, image='')
        if (self.rect):
            self.canvas.delete(self.rect)         
            
        if self.verbose:
            print ("playing video "+self.current_track['location'], flush=True)
        
        # set subtitle options
        subop=""
        if (self.current_track['omx-subtitles'] != ''):
            subop = "--subtitles \""+self.complete_path(self.current_track['omx-subtitles'])+"\" "
            subop += "--lines "+self.current_track['omx-subtitles-numlines']+" --font-size 40 "
        
        # kill off any zombie omxplayers
        subprocess.call("killall omxplayer omxplayer.bin", shell=True)
        
        self.omx = OMXDriver(self.verbose)
        self.omx.play(self.complete_path(self.current_track['location']), subop)
        self.check_video_loop()
        
        
    def update_image(self):
        if (self.annot):
            self.canvas.delete(self.annot)
        if (self.img):
            self.canvas.itemconfig(self.image_on_canvas, image='')
        if (self.rect):
            self.canvas.delete(self.rect)
            
        self.img = ImageTk.PhotoImage(Image.open(self.complete_path(self.current_track["location"])))
        
        # figure out wrap width for text and create wrapped text
        # if image width is <1800px then use image width to get wrap width
        # if image width is >=1800px then wirte text across top in a black box
        final_text=''
        img_width = self.img.width()
        if (img_width < 1800):
            text_width = int((1920 - img_width) / 27)
            trip_wrapped_text = textwrap.fill(self.current_track["trip-text"],
                                              width=text_width, break_long_words=False)
            annot_wrapped_text = textwrap.fill(self.current_track["annot-text"],
                                               width=text_width, break_long_words=False)
            final_text = trip_wrapped_text+"\n\n"+annot_wrapped_text
            self.annot = self.canvas.create_text(1,10,text=final_text,anchor=NW,fill="white",
                                                 font=("Helvetica",20,"bold"))
        else:
            text_width = 140
            final_text = self.current_track["trip-text"]
            if (self.current_track["annot-text"] != ''):
                final_text += " - " + self.current_track["annot-text"]
            final_text = textwrap.fill(final_text, width=text_width, break_long_words=False)
            self.annot = self.canvas.create_text(1,10,text=final_text,anchor=NW,fill="white",
                                                 font=("Helvetica",20,"bold"))
            bbox = self.canvas.bbox(self.annot)
            self.rect = self.canvas.create_rectangle(bbox, outline="black", fill="black")
            self.canvas.tag_raise(self.annot,self.rect)

        self.canvas.itemconfig(self.image_on_canvas, image = self.img)
        self.image_timer = self.main.after(self.duration, self.next_track)


    def complete_path(self,track_file):
        #  complete path of the filename of the selected entry
        if track_file != '' and track_file[0]=="+":
            track_file=self.media_home+track_file[1:]
        return track_file

    def quit(self,event):
        self.main.destroy()


parser = argparse.ArgumentParser()
parser.add_argument("--jsonfile", help="JSON file with tracks.", required=True)
parser.add_argument("--mediadir", help="Root directory for media.", required=True)
parser.add_argument("--timeout", help="Number of seconds for PIR timeout (Default 120).", default=120)
parser.add_argument("--duration", help="Number of seconds images are shown (Default 8).", default=8)
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


root = Tk()
MainWindow(root, args.jsonfile, args.mediadir, args.timeout, args.duration, args.verbose)
root.mainloop()
