import os
import pexpect
import re
import sys
import signal
import subprocess

from threading import Thread
from time import sleep

"""
pp_omxdriver from https://github.com/KenT2/pipresents-next
and modified for this project

 External commands
 ----------------------------
 __init__ just creates the instance and initialises variables (e.g. omx=OMXPlayer())
 play -  plays a track
 pause_on  - pauses the video
 pause_off - unpauses the video
 terminate - Stops a video playing. Used when aborting an application.
 kill - kill off omxplayer when it hasn't terminated at the end of a track.

 Also is_running() tests whether the sub-process running omxplayer is present.

"""

class OMXDriver(object):

    _STATUS_REXP = "M:\s*(\w*)\s*V:.+\s+([-\d\.]+)s\/"
    _DONE_REXP = "have a nice day.*"

    # launch video with volume at lowest level (i.e. muted)
    _LAUNCH_CMD = '/usr/bin/omxplayer -s --layer 2 --no-osd --vol -6000 '

    def __init__(self, verbose):
        self.paused=False
        self._process=None
        self.verbose = verbose
        self.muted = True
        self.dir_path = os.path.dirname(os.path.realpath(__file__))

    def control(self,char):
        self._process.send(char)
        
    def pause_on(self):
        # if already paused, then don't need to do anything
        if (self.paused): return
        self.paused = True
        # uses pngview to put the text "Paused..." as a png in the lower left corner of the screen
        # pngview should be in a standard path directory, e.g. /usr/bin
        subprocess.call("pngview -b 0 -l 3 -x 10 -y 1000 "+self.dir_path+"/paused.png &",shell=True)
        self._process.send('p')

    def pause_off(self):
        # if already unpaused, then don't need to do anything
        if (not self.paused): return
        self.paused = False
        # kill pngview to remove "Paused..." text
        subprocess.call("killall -9 pngview", shell=True)
        self._process.send('p')
        
    def mute(self):
        self.muted = True
        # This crazy command sends a message to omxplayer using
        # dbus to set the volume to it's lowest value
        subprocess.call("export DBUS_SESSION_BUS_ADDRESS=$(cat /tmp/omxplayerdbus.${USER:-root}); dbus-send --print-reply --session --reply-timeout=500 --dest=org.mpris.MediaPlayer2.omxplayer /org/mpris/MediaPlayer2 org.freedesktop.DBus.Properties.Set string:\"org.mpris.MediaPlayer2.Player\" string:\"Volume\" double:0.0", shell=True)

    def unmute(self):
        self.muted = False
        # This crazy command sends a message to omxplayer using
        # dbus to set the volume to it's highest value (i.e. the max volume set for the monitor by the user) 
        subprocess.call("export DBUS_SESSION_BUS_ADDRESS=$(cat /tmp/omxplayerdbus.${USER:-root}); dbus-send --print-reply --session --reply-timeout=500 --dest=org.mpris.MediaPlayer2.omxplayer /org/mpris/MediaPlayer2 org.freedesktop.DBus.Properties.Set string:\"org.mpris.MediaPlayer2.Player\" string:\"Volume\" double:1.0", shell=True)
    
    def seek(self, secs):
        # seek time is in microsecs, so multiply by 1 million
        subprocess.call("export DBUS_SESSION_BUS_ADDRESS=$(cat /tmp/omxplayerdbus.${USER:-root}); dbus-send --print-reply=literal --session --dest=org.mpris.MediaPlayer2.omxplayer /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Seek int64:"+str(1000000*secs), shell=True)

    def pause(self):
        self._process.send('p')       
        if not self.paused:
            self.paused = True
        else:
            self.paused=False

    def play(self, track, options):
        self._pp(track, options,False)

    def prepare(self, track, options):
        self._pp(track, options,True)
    
    def show(self):
        # unpause to start playing
        self._process.send('p')
        self.paused = False

    def stop(self):
        if self._process != None:
            self._process.send('q')

    # kill the subprocess (omxplayer.bin). Used for tidy up on exit.
    def terminate(self,reason):
        self.terminate_reason=reason
        if self._process != None:
            self._process.send('q')
        
    def terminate_reason(self):
        return self.terminate_reason
    

   # test of whether _process is running
    def is_running(self):
        return self._process.isalive()
    

    # kill off omxplayer when it hasn't terminated at the end of a track.
    # send SIGINT (CTRL C) so it has a chance to tidy up daemons and omxplayer.bin
    def kill(self):
        self._process.kill(signal.SIGINT)


# ***********************************
# INTERNAL FUNCTIONS
# ************************************

    def _pp(self, track, options,  pause_before_play):
        self.paused=False
        self.start_play_signal = False
        self.end_play_signal=False
        self.terminate_reason=''
        track= "'"+ track.replace("'","'\\''") + "'"
        cmd = OMXDriver._LAUNCH_CMD + options +" " + track
        if self.verbose: print("Send command to omxplayer: "+ cmd, flush=True)
        self._process = pexpect.spawn(cmd)

        # uncomment to monitor output to and input from omxplayer.bin (read pexpect manual)
        #fout= file('omxlogfile.txt','w')  #uncomment and change sys.stdout to fout to log to a file
        if self.verbose: self._process.logfile = sys.stdout.buffer  # send just commands to stdout
        #self._process.logfile=fout  # send all communications to log file

        if pause_before_play:
            self._process.send('p')
            self.paused = True
            
        #start the thread that is going to monitor sys.stdout. Presumably needs a thread because of blocking
        self._position_thread = Thread(target=self._get_position)
        self._position_thread.start()

    def _get_position(self):
        self.start_play_signal = True  

        self.video_position=0.0
        self.audio_position=0.0
        
        while True:
            index = self._process.expect([OMXDriver._DONE_REXP,
                                            pexpect.TIMEOUT,
                                            pexpect.EOF,
                                          OMXDriver._STATUS_REXP]
                                            ,timeout=10)
            if index == 1:     #timeout omxplayer should not do this
                self.end_play_signal=True
                self.xbefore=self._process.before
                self.xafter=self._process.after
                self.match=self._process.match
                self.end_play_reason='timeout'
                break
                # continue
            elif index == 2:       #2 is eof omxplayer should not send this
                #eof detected
                self.end_play_signal=True
                self.xbefore=self._process.before
                self.xafter=self._process.after
                self.match=self._process.match
                self.end_play_reason='eof'
                break
            elif index==0:    #0 is done
                #Have a nice day detected
                self.end_play_signal=True
                self.xbefore=self._process.before
                self.xafter=self._process.after
                self.match=self._process.match
                self.end_play_reason='nice_day'
                break            
            else:
                #  - 3 matches _STATUS_REXP so get time stamp
                self.video_position = float(self._process.match.group(1))
                self.audio_position = 0.0

                # check to see if the omx player seconds has gone negative.
                # a fix for some older videos where omxplayer doesn't exit
                # after the end of the video
                omx_secs = float(self._process.match.group(2))
                if self.verbose: print("omx secs: '" + str(omx_secs) + "'", flush=True)
                if (omx_secs < 0):
                    self.end_play_signal=True
                    self.xbefore=self._process.before
                    self.xafter=self._process.after
                    self.match=self._process.match
                    self.end_play_reason='nice_day'

                    subprocess.call("killall omxplayer omxplayer.bin", shell=True)

                    break

            #sleep is Ok here as it is a seperate thread. self.widget.after has
            #funny effects as its not in the main thread.
            sleep(0.05)   # stats output rate seem to be about 170mS.

