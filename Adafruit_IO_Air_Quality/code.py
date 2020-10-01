import time
import board
import busio
from digitalio import DigitalInOut, Direction, Pull
from simpleio import map_range
import adafruit_pm25
import adafruit_bme280


# Connect to a PM2.5 sensor over UART
uart = busio.UART(board.TX, board.RX, baudrate=9600)
pm25 = adafruit_pm25.PM25_UART(uart)

# Connect to a BME280 sensor over I2C
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

def calculate_aqi(pm_sensor_reading):
    """Returns a calculated air quality index (AQI)
    and category as a tuple.
    NOTE: The AQI returned by this function should ideally be measured
    using the 24-hour concentration average. Calculating a AQI without
    averaging will result in higher AQI values than expected.
    :param float pm_sensor_reading: Particulate matter sensor value.

    """
    # Check sensor reading using EPA breakpoint (Clow-Chigh)
    if 0.0 <= pm_sensor_reading <= 12.0:
        # AQI calculation using EPA breakpoints (Ilow-IHigh)
        aqi = map_range(int(pm_sensor_reading), 0, 12, 0, 50)
        aqi_condition = "Good"
    elif 12.1 <= pm_sensor_reading <= 35.4:
        aqi = map_range(int(pm_sensor_reading), 12, 35, 51, 100)
        aqi_condition = "Moderate"
    elif 35.5 <= pm_sensor_reading <= 55.4:
        aqi = map_range(int(pm_sensor_reading), 36, 55, 101, 150)
        aqi_condition = "Unhealthy for Sensitive Groups"
    elif 55.5 <= pm_sensor_reading <= 150.4:
        aqi = map_range(int(pm_sensor_reading), 56, 150, 151, 200)
        aqi_condition = "Unhealthy"
    elif 150.5 <= pm_sensor_reading <= 250.4:
        aqi = map_range(int(pm_sensor_reading), 151, 250, 201, 300)
        aqi_condition = "Very Unhealthy"
    elif 250.5 <= pm_sensor_reading <= 350.4:
        aqi = map_range(int(pm_sensor_reading), 251, 350, 301, 400)
        aqi_condition = "Hazardous"
    elif 350.5 <= pm_sensor_reading <= 500.4:
        aqi = map_range(int(pm_sensor_reading), 351, 500, 401, 500)
        aqi_condition = "Hazardous"
    else:
        print("Invalid PM2.5 concentration")
        aqi = -1
        aqi_condition = None
    return aqi, aqi_condition

def sample_aq_sensor():
    """Samples PM2.5 sensor
    over a 2.3 second sample rate.

    """
    aq_reading = 0
    aq_samples = []

    # initial timestamp
    time_start = time.monotonic()
    # sample pm2.5 sensor over 2.3 sec sample rate
    while (time.monotonic() - time_start <= 2.3):
        try:
            aqdata = pm25.read()
            aq_samples.append(aqdata["particles 25um"])
        except RuntimeError:
            print("Unable to read from sensor, retrying...")
            continue
        # pm sensor output rate of 1s
        time.sleep(1)
    # average sample reading / # samples
    for sample in range(len(aq_samples)):
        aq_reading += aq_samples[sample]
    aq_reading = aq_reading / len(aq_samples)
    aq_samples.clear()
    return aq_reading

def read_bme280(is_celsius=False):
    """Returns temperature and humidity
    from BME280 environmental sensor, as a tuple.

    :param bool is_celsius: Returns temperature in degrees celsius
                            if True, otherwise fahrenheit.
    """
    humidity = bme280.humidity
    temperature = bme280.temperature
    if not is_celsius:
        temperature = temperature * 1.8 + 32
    return temperature, humidity



while True:
    # TODO: Sample every 10min.
    # Air Quality
    aqi_reading = sample_aq_sensor()
    aqi_index, aqi_condition = calculate_aqi(aqi_reading)
    print("AQI: %d"%aqi_index)
    print("Condition: %s"%aqi_condition)
    # temp and humidity
    temperature, humidity = read_bme280()
    print("Temperature: %0.1f F" % temperature)
    print("Humidity: %0.1f %%" % humidity)
