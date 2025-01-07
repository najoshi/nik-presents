#!/usr/bin/python3

import json
import os
import sys
import textwrap
import subprocess
import re

trackdict = {}
extratext = {}

def load_extra_text(dirpath):
    global extratext
    extratext = {}

    if os.path.isfile(dirpath):
        dirpath = os.path.dirname(dirpath)

    if os.path.exists(dirpath+"/extra_text.txt"):
        efile = open(dirpath+"/extra_text.txt", "r", encoding='latin1')
        for fname in efile:
            fname = fname.strip()
            annot = efile.readline().strip()

            extratext[fname] = annot


def process_image(imgfile):
    bname = os.path.basename(imgfile)
    triptext = os.path.basename(os.path.dirname(imgfile))

    record ={"type" : "image", 
            "location" : "+/"+imgfile,
            "trip-text" : triptext
            }

    if bname in extratext:
        record["annot-text"] = extratext[bname]

    trackdict["tracks"].append(record)


def process_video(vidfile):
    bname = os.path.basename(vidfile)
    triptext = os.path.basename(os.path.dirname(vidfile))

    subtext = triptext
    if bname in extratext:
        subtext += " - " + extratext[bname]

    record ={"type" : "video", 
            "location" : "+/"+vidfile,
            }

    subtext = "\n".join(textwrap.wrap(subtext, width=53))
    duration_string = subprocess.check_output("ffprobe -i \""+vidfile+"\" -show_format -v quiet | grep duration", shell=True, text=True).strip()
    ss = re.search(r'duration=(\d+?)\.(\d\d\d)', duration_string)
    sec = ss.group(1)
    msec = ss.group(2)

    
    subtitles_file = vidfile + ".srt"
    sf = open(subtitles_file,"w")
    for i in range(int(sec)+1):
        sf.write(f"{i+1}\n")
        if i < int(sec):
            sf.write(f"00:00:{i},000 --> 00:00:{i+1},000\n")
        elif msec != "000":
            sf.write(f"00:00:{i},000 --> 00:00:{i},{msec}\n")

        sf.write(f"{subtext} [{i}s/{sec}s]\n\n")
    sf.close()

    record["subtitles-file"] = "+/" + subtitles_file
    trackdict["tracks"].append(record)


def process_file(file):
    print ("Processing",file)

    imgexts = ('.jpg','JPG','.jpeg','.JPEG','.png','.PNG')
    videxts = ('.mp4','.MP4','.MOV','.mov','.mpg','.MPG','.avi','.AVI','.m4v','.M4V','.mkv','.MKV')

    if file.endswith(imgexts):
        process_image(file)
    elif file.endswith(videxts):
        process_video(file)
    else:
        print("WARNING: File format for file",file,"not recognized.")


def process_dir(dirpath):
    dirpath = dirpath.rstrip("/")
    dircontent = os.listdir(dirpath)
    dircontent.sort()
    files = [dirpath+"/"+f for f in dircontent if os.path.isfile(dirpath+"/"+f)]

    load_extra_text(dirpath)

    for file in files:
        process_file(file)



if (len(sys.argv) < 3):
    print("Usage: "+sys.argv[0]+" <json file> <media file> [media file ...]")
    print("Must have json file and at least one media file.\nIf json file exists, it will append tracks to the json, otherwise it will create a new json file.")
    sys.exit()

if not sys.argv[1].endswith(".json"):
    print("First argument must be a json file ending in '.json'.")
    sys.exit()


if (not os.path.exists(sys.argv[1])):
    trackdict = {"tracks" : []}
else:
    with open(sys.argv[1], 'r') as jfile:
        data = jfile.read()
    trackdict = json.loads(data)


for path in sys.argv[2:]:
    print(path)

    if os.path.isdir(path):
        process_dir(path)
    else:
        load_extra_text(path)
        process_file(path)



json_object = json.dumps(trackdict, indent=2)
with open(sys.argv[1], 'w', encoding='latin1') as outfile:
    outfile.write(json_object)

