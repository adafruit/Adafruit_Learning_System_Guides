# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3

# pylint: disable=unused-import
import json
from subprocess import Popen, PIPE
from datetime import datetime, timezone
import requests
import displayio
import adafruit_imageload
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.circle import Circle
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import Twin, TwinProperties, QuerySpecification, QueryResult
from azure.eventhub import EventHubConsumerClient, TransportType
from blinka_displayio_pygamedisplay import PyGameDisplay

# ***

#  UPDATE THESE VARIABLES WITH YOUR IOT HUB INFORMATION

#  event hub compatible end point from the built-in endpoints page
event_connection = "YOUR-EVENT-HUB-CONNECTION-STRING-HERE"
#  Primary Connection String with registry read and service connect rights
#  managed on shared access polices page
status_connection = "YOUR-STATUS-CONNECTION-STRING-HERE"

#  iot hub subscription ID
#  found on the overview of your iot hub
#  format: ########-####-####-############
subscription_id = "YOUR-SUBSCRIPTION-ID-HERE"

#  device id's (device names in iot hub)
qt_py = "YOUR-QT-PY-DEVICE-HERE"
tft_feather = "YOUR-TFT-FEATHER-DEVICE-HERE"
s3_feather = "YOUR-S3-FEATHER-DEVICE-HERE"

# ***

#  array of devices
devices = [qt_py, tft_feather, s3_feather]

#  create display
display = PyGameDisplay(width=1920, height=1080)

#  open bitmap background with imageload
bitmap, palette = adafruit_imageload.load(
    "/home/pi/azure_pi/piBG_0.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)

background = displayio.TileGrid(bitmap, pixel_shader=palette)

#  load font files
font_file = "/home/pi/azure_pi/OstrichSans-Heavy-88.bdf"
smallFont_file = "/home/pi/azure_pi/OstrichSans-Heavy-60.bdf"
font = bitmap_font.load_font(font_file)
small_font = bitmap_font.load_font(smallFont_file)

#  text objects
#  co2 data
co2_text = label.Label(font, text = "500", color = 0xFFFFFF, x = 611, y =800)

#  living room data
lr_temp = label.Label(font, text = "72°F", color = 0xFFFFFF, x = 90, y = 424)
lr_humid = label.Label(font, text = "52%", color = 0xFFFFFF, x = 405, y = 424)
lr_press = label.Label(font, text = "1005", color = 0xFFFFFF, x = 715, y = 424)

#  bedroom data
bd_temp = label.Label(font, text = "72°F", color = 0xFFFFFF, x = 1050, y =424)
bd_humid = label.Label(font, text = "52%", color = 0xFFFFFF, x = 1365, y =424)
bd_press = label.Label(font, text = "1005", color = 0xFFFFFF, x = 1675, y =424)

#  cost, timestamp and last device check-in text
timestamp_text = label.Label(small_font, text = "00:00AM 00/00/00",
                             color = 0xFFFFFF, x = 1216, y =886)
lastDevice_text = label.Label(small_font, text = "device",
                              color = 0xFFFFFF, x = 1450, y =805)
cost_text = label.Label(small_font, text = "$0.00",
                        color = 0xFFFFFF, x = 1511, y =734)

#  status circles, defaults to white
qt_status = Circle(908, 695, 22, fill=0xFFFFFF)
lr_status = Circle(908, 52, 22, fill=0xFFFFFF)
bd_status = Circle(1869, 52, 22, fill=0xFFFFFF)

#  array of status circles
status_circles = [qt_status, lr_status, bd_status]

#  array of display objects
display_objects = [background, co2_text, lr_temp, lr_humid, lr_press,
                   bd_temp, bd_humid, bd_press, timestamp_text, lastDevice_text,
                   cost_text, qt_status, lr_status, bd_status]

#  display group
main_group = displayio.Group()

#  add all display objects from array to the display group
for x in display_objects:
    main_group.append(x)

display.root_group = main_group

#  convert UTC time to local timezone
def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

#  function for an incoming event from one of the devices
# pylint: disable=too-many-locals
def on_event_batch(partition_context, events):
    #  gets bearer token from azure cli in terminal
    cost_json_index = 0
    output = Popen(['az', 'account', 'get-access-token'], stdout=PIPE)
    #  parses the output into a json and grabs the bearer token
    bear = json.loads(output.communicate()[0].decode('utf-8').strip())
    #  creates headers to include with GET HTTP request for cost data
    headers = {'Authorization': 'Bearer ' + bear['accessToken'], 'Content-Type': 'application/json'}
    #  updates request URL with your subscription ID
    # pylint: disable=line-too-long
    url = "https://management.azure.com/subscriptions/{}/providers/Microsoft.Consumption/usageDetails?api-version=2021-10-01".format(subscription_id)
    #  makes HTTP request
    response = requests.get(url, headers=headers)
    #  packs the HTTP response into a JSON
    feed = response.json()
    #  grabs the cost per day from the JSON feed
    cost = feed['value'][cost_json_index]['properties']['costInBillingCurrency']
    #  the JSON index for cost can move depending on the data recieved
    #  adjusts index until a value is recieved
    while cost == 0:
        cost_json_index += 1
        cost = feed['value'][cost_json_index]['properties']['costInBillingCurrency']
    #  iterates through incoming events
    for event in events:
        #  gets timestamp for event
        clock = utc_to_local(event.enqueued_time)
        #  calculates the month to date cost based on the date
        month_cost = cost*((float(clock.strftime("%d")) - 1))
        round(month_cost, 2)
        #  updates cost text
        cost_text.text = "$%.2f" % month_cost
        #  updates timestamp text
        timestamp_text.text = clock.strftime("%I:%M%p %m/%d/%y")
        #  gets the incoming event as a JSON feed
        telemetry = event.body_as_json()
        #  grabs the device ID from the JSON
        device = event.system_properties[b'iothub-connection-device-id']
        #  converts the device ID to a string
        string_device = device.decode("utf-8")
        #  updates last device text
        lastDevice_text.text = string_device
        #  if the device is the qt_py
        if string_device == qt_py:
            #  update co2 text
            co2_text.text = str(telemetry['CO2'])
        #  if the device is the tft feather
        if string_device == tft_feather:
            #  update living room sensor text
            lr_temp.text = "%s°F" % str(telemetry['Temperature'])
            lr_humid.text = "%s%%" % str(telemetry['Humidity'])
            lr_press.text = str(telemetry['Pressure'])
        #  if the device is the s3 feather
        if string_device == s3_feather:
            #  update bedroom sensor text
            bd_temp.text = "%s°F" % str(telemetry['Temperature'])
            bd_humid.text = "%s%%" % str(telemetry['Humidity'])
            bd_press.text = str(telemetry['Pressure'])
    #  iterate through the status circles
    for d in range(0, 3):
        #  get connection status of all 3 devices using device twin
        twin = status_client.get_twin(devices[d])
        #  if a device is connected, make the status circle green
        if twin.connection_state == 'Connected':
            status_circles[d].fill = 0x00FF00
        #  if a device is disconnected, make the status circle red
        if twin.connection_state == 'Disconnected':
            status_circles[d].fill = 0xFF0000
    #  update the read partition from event hub
    partition_context.update_checkpoint()
#  in case of error with an incoming event
def on_error(partition_context, error):
    if partition_context:
        print("An exception: {} occurred during receiving from Partition: {}.".format(
            partition_context.partition_id,
            error
        ))
    else:
        print("An exception: {} occurred during the load balance process.".format(error))
#  connect to event hub
client = EventHubConsumerClient.from_connection_string(
    conn_str = event_connection,
    consumer_group = "$default",
)
#  connect to device twin
status_client = IoTHubRegistryManager(status_connection)

#  while the display is active
while display.running:
    try:
        #  recieve incoming events
        client.receive_batch(
            on_event_batch = on_event_batch,
            on_error = on_error
        )
    #  keyboard exception
    except KeyboardInterrupt:
        print("Receiving has ")
