#!/bin/bash

sleep 10
export DBUS_SESSION_BUS_ADDRESS=$(cat /tmp/omxplayerdbus.${USER:-root})
/usr/bin/python3 -u /home/pi/nik-presents/nik_presents.py --jsonfile /media/pi/Seagate\ Expansion\ Drive/media/np.json --mediadir /media/pi/Seagate\ Expansion\ Drive --verbose &> /home/pi/log.txt
