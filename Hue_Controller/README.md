# hue_controller

Firmware for motion/light/time driven hue lighting controller.

Use with the Arduino IDE, with FeatherM0 selected as the board.

Run the setup.sh script first to build secrets.h.

| Env Var     | meaning                                |
| ----------- | --------------------------------------:|
| WIFI_SSID   | The SSID of your Wifi                  |
| WIFI_PASS   | the password for your Wifi             |
| HUE_USER    | Your user id for the HUE developer API |
| DARKSKY_KEY | Your user id for the darksky.net API   |
| AIO_USER    | Your Adafruit IO username              |
| AIO_KEY     | Your Adafruit IO secret key            |
