#!/bin/bash

DIR=${1#/home/joshi/digital_media_frame_touch/}
DIR=${DIR//$'\n'}

cd /home/joshi/digital_media_frame_touch
# ./media_chooser.pl "${NAUTILUS_SCRIPT_SELECTED_FILE_PATHS#/home/joshi/digital_media_frame/}" &> /tmp/tmp.sh
./scripts/media_chooser.pl "$DIR" &> /home/joshi/digital_media_frame_touch/mc.err
# echo -n "${NAUTILUS_SCRIPT_SELECTED_FILE_PATHS#/home/joshi/digital_media_frame/}" &> /tmp/tmp.sh
