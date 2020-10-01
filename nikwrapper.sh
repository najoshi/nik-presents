#!/bin/bash

sleep 10
/usr/bin/python3 -u /home/pi/nik-presents/nik_presents_pi3.py --jsonfile /media/pi/Seagate\ Expansion\ Drive/media/np_pi3.json --mediadir /media/pi/Seagate\ Expansion\ Drive --verbose &> /home/pi/log.txt
