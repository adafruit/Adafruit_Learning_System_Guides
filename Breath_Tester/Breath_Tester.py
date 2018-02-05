import time
import board
import busio
import adafruit_sgp30

i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)

# Create library object on our I2C port
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
sgp30.iaq_init()
sgp30.set_iaq_baseline(0x8973, 0x8aae)

# highest tVOC recorded in 30 seconds
highest_breath_result = 0

def warmup_message():

    warmup_time = 20 
    warmup_counter = 0

    co2eq, tvoc = sgp30.iaq_measure()           # initial read required to get sensor going

    print()
    print("Warming Up [%d seconds]..." % warmup_time)

    while ( warmup_counter <= 20 ):
        print('.', end='')
        time.sleep(1)
        warmup_counter += 1

def get_breath_reading():

    breath_time = 30                            # seconds to record breath reading
    breath_counter = 0                          # one second count up to breath_time value
    breath_saves = [0] * ( breath_time + 1 )    # initialize list with empty values

    print()
    print("We will collect breath samples for 30 seconds.")
    print("Take a deep breath and exhale into the straw.")
    input(" *** Press a key when ready. *** ")
    print()

    while ( breath_counter <= breath_time ):
        co2eq, tvoc = sgp30.iaq_measure()
        breath_saves[breath_counter] = tvoc
        print(tvoc, ', ', end='')
        time.sleep(1)
        breath_counter += 1

    breath_saves = sorted(breath_saves)
    highest_breath_result = breath_saves[breath_counter - 1] 

    return(highest_breath_result)

# show the highest reading recorded
def show_results(highest_breath_result):
    print()
    print()
    print("peak VOC reading:", highest_breath_result)
    print()
    input("Press any key to test again")
    print()

# main
while True:
    warmup_message()
    highest_breath_result = get_breath_reading()
    show_results(highest_breath_result)
