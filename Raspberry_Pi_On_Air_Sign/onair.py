#!/usr/bin/python

# "ON AIR" sign controller for Raspberry Pi.  Polls Ustream and Google+
# Hangouts for online status, activates PowerSwitch Tail II as needed,
# turns on lamp.  Requires RPi.GPIO library.
#
# Written by Phil Burgess / Paint Your Dragon for Adafruit Industries.
#
# Adafruit invests time and resources providing this open source code,
# please support Adafruit and open-source hardware by purchasing products
# from Adafruit!
#
# Resources:
# http://www.adafruit.com/products/268
# http://www.markertek.com/Studio-Gear/Studio-Warning-Lights-Signs.xhtml

import bisect, calendar, json, time, urllib
import RPi.GPIO as GPIO

pin = 24   # PowerSwitch Tail connects to this GPIO pin

# Ustream settings -----------------------------------------------------------
# 'uKey' is your Developer API key (request one at developer.ustream.tv).
# 'uChannel' is Ustream channel to monitor.
uKey     =  'PUT_USTREAM_DEVELOPER_API_KEY_KERE'
uChannel =  'adafruit-industries'
uUrl     = ('http://api.ustream.tv/json/channel/' + uChannel +
            '/getValueOf/status?key='             + uKey )

# Google+ settings -----------------------------------------------------------
# 'gKey' is your API key from the Google APIs API Access page (need to switch
# on G+ on API Services page first).  'gId' is the account ID to monitor (can
# find this in the URL of your profile page, mild nuisance but ID is used
# because user name is not guaranteed unique.
gKey =  'PUT_GOOGLE_API_KEY_HERE'
gId  =  '112526208786662512291' # Adafruit account ID
gUrl = ('https://www.googleapis.com/plus/v1/people/' + gId +
        '/activities/public?maxResults=4&' +
        'fields=items(title,published),nextPageToken&key=' + gKey)
gOn  =  'is hanging out'  # This phrase in title indicates an active hangout

# List of starting times (HH:MM) and polling frequency (seconds) -------------
# This is to provide a more responsive 'on air' switchover time without
# blowing through search bandwidth limits.  Use more frequent checks during
# known 'likely to switch' periods, infrequent during 'out of office' times.
# Currently follows same pattern each day; doesn't have a weekly schedule.
times = [
  ("06:00",  60),  # 6am, office hours starting, poll once per minute
  ("21:25",  10),  # 9:25pm, Show & Tell starting soon, poll 6X/minute
  ("21:35",  30),  # S&T underway, reduce polling to 2X per minute
  ("21:55",  10),  # 9:55pm, AAE starting soon, poll 6X/minute again
  ("22:05",  30),  # AAE underway, slow polling to 2X per minute
  ("23:10",  60),  # AAE over (plus extra), return to once per minute
  ("00:00", 900) ] # After midnight, gone home, poll every 15 minutes

def req(url): # Open connection, read and deserialize JSON document ----------
	connection = urllib.urlopen(url)
	try:     data = json.load(connection)
	finally: connection.close()
	return data

def paginate(pageToken): # ---------------------------------------------------
	global gOnline, latestPost, timeThreshold

	# Output from Google+ API is paginated, limited to 20 items max.
	# We can't necessarily read everything in one pass, may need to
	# make repeated calls passing a "page token" from one to the next.
	response = req(
	  (gUrl + '&pageToken=' + pageToken) if pageToken else gUrl)
	for item in response['items']:
		utcTime = time.strptime(
		  item['published'].split('.', 1)[0],
		  '%Y-%m-%dT%H:%M:%S')
		seconds = calendar.timegm(utcTime) # UTC -> epoch
		if seconds > latestPost:
			# Keep track of time of most recent post.
			# If the time threshold is more than 24 hours
			# before this, it can be moved up -- otherwise
			# searches will eventually reach all the way
			# back to the last hangout which may be a full
			# week prior.
			latestPost = seconds
			t = latestPost - 60 * 60 * 24
			if(timeThreshold < t): timeThreshold = t
		if seconds < timeThreshold:
			# Time threshold reached, no on-air message
			# found in any posts newer than the threshold,
			# no hangout occurring.  Stop search.  Save
			# time of latest post as new threshold;
			# no need to search earlier than that for
			# hangouts, they won't appear retroactively.
			# (Items are in reverse chronological order.)
			gOnline       = False
			timeThreshold = latestPost
			return None # Stop search; no further pages
		if gOn in item['title']:
			# On-air message found!  Set global gOnline
			# flag, set time threshold to hangout time;
			# need to keep testing back to this time to
			# confirm hangout is still running.  (If it
			# ends, title changes and will no longer
			# contain the on-air string.  There is no
			# separate event to indicate end of hangout.)
			gOnline       = True
			timeThreshold = seconds
			return None
	return response['nextPageToken'] # Continue search on next page

# Startup --------------------------------------------------------------------

GPIO.setwarnings(False)    # Don't bug me about existing pin state
GPIO.setmode(GPIO.BCM)     # Use Broadcom pin numbers
GPIO.setup(pin, GPIO.OUT)  # Enable output
GPIO.output(pin, GPIO.LOW) # Pin off by default

# Convert times[] to a new list with units in integer minutes
mins = []
for t in times:
	x = t[0].split(":")
	mins.append([(int(x[0]) % 24) * 60 + int(x[1]), t[1]])

mins.sort() # Sort in-place in increasing order

# If first time is not midnight, insert an item there, duplicating the
# polling frequency of the last item in the list.
if mins[0][0] > 0: mins.insert(0, [0, mins[len(mins)-1][1]])

timeThreshold = latestPost = 0

while 1: # Main loop ---------------------------------------------------------

	uOnline = gOnline = False
	startTime = time.time()

	# Ustream broadcast query
	try:                 uOnline = req(uUrl)['results'] == 'live'
	except Exception, e: print "Error: {0} : {1}".format(type(e), e.args)

	# G+ hangout query
	try:
		pageToken = None
		while 1:
			pageToken = paginate(pageToken)
			if pageToken is None: break
	except Exception, e: print "Error: {0} : {1}".format(type(e), e.args)

	print 'G+ hangout: ' + ('online' if gOnline else 'offline')
	print 'Ustream   : ' + ('online' if uOnline else 'offline')
	GPIO.output(pin, GPIO.HIGH if uOnline or gOnline else GPIO.LOW)

	# Delay before next query
	try:
		n = time.time()                      # NAO
		t = time.localtime(n)                # Local time struct
		m = t.tm_hour * 60 + t.tm_min        # Convert to minutes
		i = bisect.bisect(mins, [m, 60]) - 1 # mins[] list index
		d = mins[i][1] - (n - startTime)     # Time to next poll
		if d > 0:
			print 'Waiting ' + str(d) + ' seconds'
			time.sleep(d)
	except:
		time.sleep(60)
