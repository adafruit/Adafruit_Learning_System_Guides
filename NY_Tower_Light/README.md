## New-Year-Tower-Light
IoT Tower alert we did on the last night of 2015!!

We make a tower alert that responds to github events:

- [Github] publishes repo events to a number of webhooks. But in reality, any service that speaks http can be used.
- [AWS lambda] receives the github webhooks and publishes MQTT events. [python code](lambda/)
- [Adafruit io] provides a MQTT gateway.
- A little [ESP8266 HUZZAH] receives the MQTT messages and controls the red, yellow, and green lights of a tower alert. [huzzah code](esp8266/)

The live coding video can be found on [youtube].

This code was formerly at https://github.com/adafruit/New-Year-Tower-Light/ - this has now been archived.

If you are looking to make changes/additions, please use the GitHub Issues and Pull Request mechanisms.

All code MIT License, please attribute to Adafruit Industries

Please consider buying your parts at [Adafruit.com](https://www.adafruit.com) to support open source code

[Github]: https://www.github.com/
[Adafruit io]: https://io.adafruit.com/
[ESP8266 HUZZAH]: https://www.adafruit.com/products/2471
[AWS lambda]: https://aws.amazon.com/lambda
[youtube]: https://www.youtube.com/watch?v=TnjIXlnaN00
