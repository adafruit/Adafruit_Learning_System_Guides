"""
IoT environmental sensor node.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
import board
import busio
import air_quality
import gps
import adafruit_bme280
import aio
import adafruit_logging as logging

logger = logging.getLogger('main')
logger.setLevel(logging.INFO)

gps_uart = busio.UART(board.TX, board.RX, baudrate=9600, timeout=3.000)
gps_interface = gps.Gps(gps_uart)
gps_interface.begin()

logger.debug('GPS started')

aio_interface = aio.AIO()

if aio_interface.onboard_esp:
    air_uart = busio.UART(board.D5, board.D7, baudrate=9600)
else:
    air_uart = busio.UART(board.A2, board.A3, baudrate=9600)
air = air_quality.AirQualitySensor(air_uart)

logger.debug('Air quality sensor started')

i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

reading_interval = 300.0
reading_time = time.monotonic()

time_update_interval = 3600.0
time_update_time = time.monotonic()

logger.info('Getting data from GPS')

while True:
    if gps_interface.get_fix():
        break
    logger.error('Failed getting fix... retrying')

gps_interface.read()

logger.info('Starting reading loop')

payload = {'value' : 0,
           'lat' : gps_interface.latitude,
           'lon' : gps_interface.longitude,
           'created_at' : ''}

while True:
    now = time.monotonic()

    if now >= time_update_time:
        time_update_time = now + time_update_interval
        logger.info('refreshing time')
        try:
            aio_interface.refresh_local_time()
        except RuntimeError as e:
            logger.debug('Time refresh failed with: %s', str(e))

    if now >= reading_time:
        reading_time = now + reading_interval
        logger.info('Taking a reading')

        st = time.localtime()
        timestamp = '{0}/{1:02}/{2:02} {3:2}:{4:02}:{5:02}'.format(st.tm_year,
                                                                   st.tm_mon,
                                                                   st.tm_mday,
                                                                   st.tm_hour,
                                                                   st.tm_min,
                                                                   st.tm_sec)
        payload['created_at'] = timestamp

        if air.read():
            logger.info('Air Quality pm10 standard: %d', air.pm10_standard)
            payload['value'] = air.pm10_standard
            if not aio_interface.post('environmental-sensor.pm10-std', payload):
                logger.critical('post of pm10 standard failed')
                continue

            logger.info('Air Quality pm25 standard: %d', air.pm25_standard)
            payload['value'] = air.pm25_standard
            if not aio_interface.post('environmental-sensor.pm25-std', payload):
                logger.critical('post of pm25 standard failed')
                continue

            logger.info('Air Quality pm100 standard: %d', air.pm100_standard)
            payload['value'] = air.pm100_standard
            if not aio_interface.post('environmental-sensor.pm100-std', payload):
                logger.critical('post of pm100 standard failed')
                continue

            logger.info('Air Quality pm10 env: %d', air.pm10_env)
            payload['value'] = air.pm10_env
            if not aio_interface.post('environmental-sensor.pm10-env', payload):
                logger.critical('post of pm10 env failed')
                continue

            logger.info('Air Quality pm25 env: %d', air.pm25_env)
            payload['value'] = air.pm25_env
            if not aio_interface.post('environmental-sensor.pm25-env', payload):
                logger.critical('post of pm10 env failed')
                continue

            logger.info('Air Quality pm100 env: %d', air.pm100_env)
            payload['value'] = air.pm100_env
            if not aio_interface.post('environmental-sensor.pm100-env', payload):
                logger.critical('post of pm100 env failed')
                continue

            logger.info('Air Quality particles 03um: %d', air.particles_03um)
            payload['value'] = air.particles_03um
            if not aio_interface.post('environmental-sensor.03um', payload):
                logger.critical('post of particles 03um failed')
                continue

            logger.info('Air Quality particles 05um: %d', air.particles_05um)
            payload['value'] = air.particles_05um
            if not aio_interface.post('environmental-sensor.05um', payload):
                logger.critical('post of particles 05um failed')
                continue

            logger.info('Air Quality particles 10um: %d', air.particles_10um)
            payload['value'] = air.particles_10um
            if not aio_interface.post('environmental-sensor.10um', payload):
                logger.critical('post of particles 10um failed')
                continue

            logger.info('Air Quality particles 25um: %d', air.particles_25um)
            payload['value'] = air.particles_25um
            if not aio_interface.post('environmental-sensor.25um', payload):
                logger.critical('post of particles 25um failed')
                continue

            logger.info('Air Quality particles 50um: %d', air.particles_50um)
            payload['value'] = air.particles_50um
            if not aio_interface.post('environmental-sensor.50um', payload):
                logger.critical('post of particles 50um failed')
                continue

            logger.info('Air Quality particles 100um: %d', air.particles_100um)
            payload['value'] = air.particles_100um
            if not aio_interface.post('environmental-sensor.100um', payload):
                logger.critical('post of particles 100um failed')
                continue

        logger.info('Temperature: %f', bme280.temperature)
        payload['value'] = bme280.temperature
        if not aio_interface.post('environmental-sensor.temperature', payload):
            logger.critical('post of temperature failed')
            continue

        logger.info('Humidity: %f', bme280.humidity)
        payload['value'] = bme280.humidity
        if not aio_interface.post('environmental-sensor.humidity', payload):
            logger.critical('post of humidity failed')
            continue

        logger.info('Pressure: %f', bme280.pressure)
        payload['value'] = bme280.pressure
        if not aio_interface.post('environmental-sensor.pressure', payload):
            logger.critical('post of pressure failed')
            continue

        logger.info('Waiting for next reading')
