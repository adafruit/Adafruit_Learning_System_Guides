#!/bin/sh

# Timelapse script, because timelapse options in raspistill don't power
# down the camera between captures. Script also provides a camera busy LED
# (v2 cameras don't include one) and a system halt button.
# 'gpio' command requires WiringPi: sudo apt-get install wiringpi
# Limitations: if DEST is FAT32 filesystem, max of 65535 files in directory;
# if DEST is ext4 filesystem, may have performance issues above 10K files.
# For intervals <2 sec, better just to use raspistill's timelapse feature.

# Configurable stuff...
INTERVAL=15            # Time between captures, in seconds
WIDTH=1280             # Image width in pixels
HEIGHT=720             # Image height in pixels
QUALITY=51             # JPEG image quality (0-100)
DEST=/boot/timelapse   # Destination directory (MUST NOT CONTAIN NUMBERS)
PREFIX=img             # Image prefix (MUST NOT CONTAIN NUMBERS)
HALT=21                # Halt button GPIO pin (other end to GND)
LED=5                  # Status LED pin (v2 Pi cam lacks built-in LED)
prevtime=0             # Time of last capture (0 = do 1st image immediately)

gpio -g mode $HALT up  # Initialize GPIO states
gpio -g mode $LED  out
mkdir -p $DEST         # Create destination directory (if not present)

# Find index of last image (if any) in directory, start at this + 1
FRAME=$(($(find $DEST -name "*.jpg" -printf %f\\n | sed 's/^[^1-9]*//g' | sort -rn | head -1 | sed 's/[^0-9]//g') + 1))

while :         # Forever
do
	while : # Until next image capture time
	do
		currenttime=$(date +%s)
		if [ $(($currenttime-$prevtime)) -ge $INTERVAL ]; then
			break # Time for next image cap
		fi
		# Check for halt button -- hold >= 2 sec
		while [ $(gpio -g read $HALT) -eq 0 ]; do
			if [ $(($(date +%s)-currenttime)) -ge 2 ]; then
				gpio -g write $LED 1
				shutdown -h now
			fi
		done
	done

	OUTFILE=`printf "$DEST/$PREFIX%05d.jpg" $FRAME`
	# echo $OUTFILE
	gpio -g write $LED 1
	raspistill -n -w $WIDTH -h $HEIGHT -q $QUALITY -th none -t 250 -o $OUTFILE
	gpio -g write $LED 0
	FRAME=$(($FRAME + 1)) # Increment image counter
	prevtime=$currenttime # Save image cap time
done