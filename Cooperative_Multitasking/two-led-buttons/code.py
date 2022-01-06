import asyncio
import board
import digitalio
import keypad


class Interval:
    """Simple class to hold an interval value. Use .value to to read or write."""

    def __init__(self, initial_interval):
        self.value = initial_interval


async def monitor_interval_buttons(pin_slower, pin_faster, interval):
    """Monitor two buttons: one lengthens the interval, the other shortens it.
    Change interval.value as appropriate.
    """
    # Assume buttons are active low.
    with keypad.Keys(
        (pin_slower, pin_faster), value_when_pressed=False, pull=True
    ) as keys:
        while True:
            key_event = keys.events.get()
            if key_event and key_event.pressed:
                if key_event.key_number == 0:
                    # Lengthen the interval.
                    interval.value += 0.1
                else:
                    # Shorten the interval.
                    interval.value = max(0.1, interval.value - 0.1)
                print("interval is now", interval.value)
            # Let another task run.
            await asyncio.sleep(0)


async def blink(pin, interval):
    """Blink the given pin forever.
    The blinking rate is controlled by the supplied Interval object.
    """
    with digitalio.DigitalInOut(pin) as led:
        led.switch_to_output()
        while True:
            led.value = not led.value
            await asyncio.sleep(interval.value)


async def main():
    interval1 = Interval(0.5)
    interval2 = Interval(1.0)

    led1_task = asyncio.create_task(blink(board.D1, interval1))
    led2_task = asyncio.create_task(blink(board.D2, interval2))
    interval1_task = asyncio.create_task(
        monitor_interval_buttons(board.D3, board.D4, interval1)
    )
    interval2_task = asyncio.create_task(
        monitor_interval_buttons(board.D5, board.D6, interval2)
    )

    await asyncio.gather(led1_task, led2_task, interval1_task, interval2_task)


asyncio.run(main())
