# SPDX-FileCopyrightText: Copyright (c) 2023 john park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import asyncio
from random import randint, uniform
import busio
import board
import adafruit_aw9523

# pin descriptions are based on physical LED placement
# 0 bakery window, 1 lamp1 A, 2 lamp1 B, 3 bakery sconce, 4 lamp 2, 5 music sconce a,
# 6 music sconce b, 7 music candle, 8 bakery red a, 9 bakery red b, 10 bakery green a,
# 11 bakery green b

i2c = busio.I2C(board.SCL1, board.SDA1)
leddriver = adafruit_aw9523.AW9523(i2c)

# Set all pins to outputs and LED (const current) mode
leddriver.LED_modes = 0xFFFF
leddriver.directions = 0xFFFF

window_set = [8, 10, 9, 11]  # red/green string
always_on_set = [0, 1, 2, 4]  # window and lanterns
always_on_set_maxes = [100, 30, 30, 40]  # maximum brightness per light

# lights that are always on
for n in range(len(always_on_set)):
    leddriver.set_constant_current(always_on_set[n], always_on_set_maxes[n])

async def flicker(pin, min_curr, max_curr, interval):
    while True:
        rand_max_curr = randint(min_curr, max_curr)
        for i in range(min_curr, rand_max_curr):
            leddriver.set_constant_current(pin, i)  # aw9523 pin, current out of 255
            await asyncio.sleep(0.07)
        await asyncio.sleep(uniform(0.0, interval))

async def string_lights(interval, max_curr):
    while True:
        for i in range(len(window_set)):
            # fade up
            for j in range(max_curr):
                leddriver.set_constant_current(window_set[i], j)
                print(j)
                await asyncio.sleep(interval)
        for i in range(len(window_set)):
            # fade down
            for j in range(max_curr):
                leddriver.set_constant_current(window_set[i], max_curr-j)
                print(j)
                await asyncio.sleep(interval)


async def main():
    led0_task = asyncio.create_task(flicker(3, 3, 10, 0.7))  # music candle
    led1_task = asyncio.create_task(flicker(5, 6, 12, 0.7))  # music sconce a
    led2_task = asyncio.create_task(flicker(6, 6, 12, 0.7))  # music sconce b
    led3_task = asyncio.create_task(flicker(7, 3, 10, 0.7))  # music candle
    led4_task = asyncio.create_task(string_lights(0.03, 30))
    await asyncio.gather(led0_task, led1_task, led2_task, led3_task, led4_task)

asyncio.run(main())
