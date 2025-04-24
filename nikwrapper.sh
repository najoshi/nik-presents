#!/bin/bash

sleep 10
# /usr/bin/python3 -u /home/pi/nik-presents/pi3/nik_presents_pi3.py --jsonfile /media/pi/Seagate\ Expansion\ Drive1/media/np_pi3.json --mediadir /media/pi/Seagate\ Expansion\ Drive1 &> /home/pi/log.txt

# /usr/bin/python3 -u /home/pi/nik-presents/pi3/nik_presents_pi3.py --jsonfile /media/pi/Seagate\ Expansion\ Drive1/media/np_pi3.json --mediadir /media/pi/Seagate\ Expansion\ Drive1 --verbose &> /home/pi/log.txt

/usr/bin/python3 -u /home/pi/nik-presents/pi3/nik_presents_pi3.py --jsonfile /home/pi/test_latin1.json --mediadir /media/pi/Seagate\ Expansion\ Drive1 --verbose &> /home/pi/log.txt
