#!/usr/bin/python3

import sys
import json

newtrackdict = {"tracks":[]}

with open(sys.argv[1], 'r') as jfile:
    data = jfile.read()
    trackdict = json.loads(data)

fndict={}
for fn in sys.argv[2:]:
    fndict[fn]=1

for record in trackdict["tracks"]:
    loc = record["location"][2:]
    if (loc not in fndict):
        newtrackdict["tracks"].append(record)

jout = json.dumps(newtrackdict, indent=4)
print(jout)

