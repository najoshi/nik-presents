#!/usr/bin/python3

from tkinter import *
import glob
from PIL import ImageTk,Image
import json
import sys
import vlc
from vlc import VideoMarqueeOption
import textwrap
from gpiozero import MotionSensor
import time
import subprocess
import random
import argparse
import os


class MainWindow():

    def __init__(self, main, jsonfile, media_home):

        self.media_home = media_home
        self.media_profile = ""
        self.main=main
        self.main.attributes("-fullscreen", True)
        self.main.bind("q", self.quit)

        with open(jsonfile, 'r') as jfile:
            data = jfile.read()

        self.tracks = json.loads(data)["tracks"]
        random.shuffle(self.tracks)

        # canvas for image
        self.canvas = Canvas(main, width = 1920, height = 1080, bg = "black", highlightthickness=0)
        self.canvas.pack()
        self.track_number = -1
        self.image_on_canvas = self.canvas.create_image(960, 540, anchor = CENTER)
        self.canvas.bind('<Button-1>',self.onClick)

        self.image_timer=None
        self.video_timer=None
        self.annot=None
        self.img=None
        self.paused = False
        self.pause_text=None
        self.current_track=None
        self.running = True
        self.pir = MotionSensor(17)
        self.last_motion_time = time.time()
        self.MOTION_LIMIT = 120
        
        self.pir.when_motion = self.do_motion
        self.main.after(1,self.check_limit)
        self.next_track()
        
    def check_limit(self):
        if (self.running and (time.time() > (self.last_motion_time + self.MOTION_LIMIT))):
            self.running = False
            self.pause_on()
            self.turn_off_monitor()
        self.main.after(100,self.check_limit)
        
    def do_motion(self):
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
        #print (self.current_track["type"],"X:",x)
        if (x<640):
            self.prev_track()
        elif (x>=640 and x<1280):
            if (self.paused):
                self.pause_off()
            else:
                self.pause_on()
        elif (x>=1280):
            self.next_track()

    def pause_on(self):
        if (self.paused):
            return
        self.paused = True
        
        if (self.current_track["type"] == "image"):
            self.main.after_cancel(self.image_timer)
            self.pause_text = self.canvas.create_text(1,1000,text="Paused...",anchor=NW,
                                                      fill="white",font="Helvetica 20 bold")
            
        elif (self.current_track["type"] == "video"):
            self.player.set_pause(True)
            self.player.video_set_marquee_int(VideoMarqueeOption.Enable, 1)
            self.player.video_set_marquee_int(VideoMarqueeOption.X, 10)
            self.player.video_set_marquee_int(VideoMarqueeOption.Y, 1260)
            self.player.video_set_marquee_int(VideoMarqueeOption.Size, 40)
            self.player.video_set_marquee_string(VideoMarqueeOption.Text,"Paused...")
            
    def pause_off(self):
        if (not self.paused):
            return
        self.paused = False
        
        if (self.current_track["type"] == "image"):
            self.canvas.delete(self.pause_text)
            self.image_timer = self.main.after(8000, self.next_track)
            
        elif (self.current_track["type"] == "video"):
            self.player.video_set_marquee_int(VideoMarqueeOption.Enable, 0)
            self.player.set_pause(False)


    def prev_track(self):
        self.pause_off()
        
        if (self.image_timer):
            self.main.after_cancel(self.image_timer)
        if (self.video_timer):
            self.main.after_cancel(self.video_timer)

        if (self.current_track["type"] == "video"):
            self.player.stop()
            
        self.track_number -= 1
        if self.track_number == -1:
            self.track_number = len(self.tracks)-1
            
        self.current_track = self.tracks[self.track_number]
        
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
            self.player.stop()
            
        self.track_number += 1
        if self.track_number == len(self.tracks):
            random.shuffle(self.tracks)
            self.track_number = 0
            
        self.current_track = self.tracks[self.track_number]
        
        if (self.current_track["type"] == "image"):
            self.update_image()
        elif (self.current_track["type"] == "video"):
            self.play_video()
            
    def check_video_loop(self):
        if self.player.get_state() == vlc.State.Ended:
            self.player.stop()
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
            
        #make the Tkinter window appear above VLC's
        #black background x window so that clicks work.
        self.main.iconify()
        self.main.update()
        self.main.after(1000, lambda: self.main.deiconify())
            
        i_opts=['--no-xlib','--vout','mmal_xsplitter','--mmal-layer=1','--mmal-display=HDMI-1',
                '--no-video-title-show','--quiet']
        
        if (self.current_track['vlc-subtitles']):
            i_opts += ['--sub-file',self.complete_path(self.current_track['vlc-subtitles'])]
            
        self.vlc_instance = vlc.Instance(i_opts)
        self.media = self.vlc_instance.media_new(self.complete_path(self.current_track['location']))
        self.player = vlc.MediaPlayer(self.vlc_instance,'',(''))
        self.player.set_media(self.media)
        self.player.set_fullscreen(True)
        self.player.play()
        
        self.check_video_loop()
        
        
    def update_image(self):
        if (self.annot):
            self.canvas.delete(self.annot)
        if (self.img):
            self.canvas.itemconfig(self.image_on_canvas, image='')
            
        self.img = ImageTk.PhotoImage(Image.open(self.complete_path(self.current_track["location"])))
        
        #figure out width for text
        #text_font = tkfont.Font(family="Helvetica", size=20, weight="bold")
        #text_pixels = text_font.measure(self.current_track["trip-text"])
        final_text=''
        img_width = self.img.width()
        if (img_width < 1800):
            text_width = int((1920 - img_width) / 40)
            trip_wrapped_text = textwrap.fill(self.current_track["trip-text"],
                                              width=text_width, break_long_words=False)
            annot_wrapped_text = textwrap.fill(self.current_track["annot-text"],
                                               width=text_width, break_long_words=False)
            final_text = trip_wrapped_text+"\n\n"+annot_wrapped_text
        else:
            text_width = 140
            final_text = textwrap.fill(self.current_track["trip-text"]+" - "+
                                       self.current_track["annot-text"], width=text_width,
                                       break_long_words=False)
        
        self.canvas.itemconfig(self.image_on_canvas, image = self.img)
        self.annot = self.canvas.create_text(1,40,text=final_text,anchor=NW,fill="white",
                                             font="-*-lucidatypewriter-medium-r-*-*-*-240-*-*-*-*-*-*")
        
        self.image_timer = self.main.after(8000, self.next_track)
        
    def complete_path(self,track_file):
        #  complete path of the filename of the selected entry
        if track_file != '' and track_file[0]=="+":
            track_file=self.media_home+track_file[1:]
        return track_file

    def quit(self,event):
        self.main.destroy()


parser = argparse.ArgumentParser()
parser.add_argument("--jsonfile", help="JSON file with tracks", required=True)
parser.add_argument("--mediadir", help="Root directory for media", required=True)
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
MainWindow(root,args.jsonfile,args.mediadir)
root.mainloop()