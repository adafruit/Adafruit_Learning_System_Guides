# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import supervisor
import rotaryio
import keypad
import board
import busio
import displayio
from adafruit_display_text import label
from fourwire import FourWire
from adafruit_st7789 import ST7789
from adafruit_bitmap_font import bitmap_font
from adafruit_tmc2209 import TMC2209

displayio.release_displays()

RAILS = 520 # length of rails in mm
microsteps = 128
gear_ratio = 41 / 16

shot_velocities = [
    20,
    15,
    10
]

keys = keypad.Keys((board.D2, board.A2, board.A3), value_when_pressed=False, pull=True)

encoder = rotaryio.IncrementalEncoder(board.D7, board.D6)
last_position = None

spi = board.SPI()
tft_cs = board.D10
tft_dc = board.D8

display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.D9)

display = ST7789(display_bus, width=240, height=240, rowstart=80, auto_refresh=False)

splash = displayio.Group()
display.root_group = splash

bitmap = displayio.OnDiskBitmap(open("/icons.bmp", "rb"))

grid_bg = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader,
                             tile_height=100, tile_width=100,
                             x=(display.width - 100) // 2,
                             y=(display.height - 100) // 2)
splash.append(grid_bg)

text_group = displayio.Group()
font = bitmap_font.load_font("/Arial-14.bdf")
title_text = "Camera Slider"
title_area = label.Label(font, text=title_text, color=0xFFFFFF)
title_area.anchor_point = (0.5, 0.0)
title_area.anchored_position = (display.width / 2, 25)
text_group.append(title_area)
splash.append(text_group)

font = bitmap_font.load_font("/Arial-14.bdf")
text_area = label.Label(font, text="", color=0xFFFFFF)
text_area.anchor_point = (0.5, 1.0)
text_area.anchored_position = (display.width / 2, display.height - 25)
text_group.append(text_area)

uart = busio.UART(tx=board.TX, rx=board.RX, baudrate=115200, timeout=0.1)

driver1 = TMC2209(uart=uart, addr=0)
driver2 = TMC2209(tx_pin=board.D4, rx_pin=board.D5, addr=0)

version1 = driver1.version
version2 = driver2.version
print(f"TMC2209 #1 Version: 0x{version1:02X}")
print(f"TMC2209 #2 Version: 0x{version2:02X}")

driver1.microsteps = microsteps
print(driver1.microsteps)
driver2.microsteps = microsteps
print(driver2.microsteps)

STEPS_PER_MM = 200 * microsteps / 8
driver1.direction = False
driver2.direction = True

last_pos = 0
select = 0
menu = 0
time_mode = 0
shot_mode = 0
timelapse = True
movement_time = 0
titles = ["Camera Slider", "Motor 1", "Motor 2", "Mode",
          "Timelapse", "One-Shot", "Start?", "Running"]

home_text = ["Press to Begin", "0"]
motor1_text = ["Slide to Start Point", "0"]
motor2_text = ["Move to Start", "Move to End", "0"]
mode_text = ["Timelapse", "One-Shot"]
time_text = ["1", "5", "10", "15", "30"]
shot_speeds = [10, 5, 2]
speeds = []
shot_text = ["Slow", "Medium", "Fast"]
start_text = ["Go!", 0]
running_text = ["STOP!", "Pause/Resume"]
running_icons = [6, 7]
mode_icons = [3, 4]
sub_titles = [home_text, motor1_text, motor2_text, mode_text,
              time_text, shot_text, start_text, running_text]
motor2_coordinates = [0.0, 0.0]
text_area.text = home_text[0]
display.refresh()

def adv_menu(m):
    m = (m + 1) % 8
    title_area.text = titles[m]
    sub = sub_titles[m]
    if m == 4:
        grid_bg[0] = 3
    elif m == 5:
        grid_bg[0] = 4
    elif m > 5:
        grid_bg[0] = m - 1
    else:
        grid_bg[0] = m
    text_area.text = sub[0]
    display.refresh()
    return m

motor1_movement = {
    "is_active": False,
    "current_step": 0,
    "total_steps": 0,
    "start_pos": 0,
    "end_pos": 0,
    "step_direction": 1,
    "last_step_time": 0,
    "step_interval": 0,
    "is_paused": False,
    "toggle_pause": False,
    "stop_requested": False
}

motor2_movement = {
    "is_active": False,
    "current_step": 0,
    "total_steps": 0,
    "start_pos": 0,
    "end_pos": 0,
    "step_direction": 1,
    "last_step_time": 0,
    "step_interval": 0,
    "is_paused": False,
    "toggle_pause": False,
    "stop_requested": False
}

# pylint: disable=too-many-branches, too-many-statements, inconsistent-return-statements

def calculate_linear_velocity(steps_per_second, clock_frequency=12000000,
                              micro=128, scaling_factor=6):
    frequency = steps_per_second * micro
    vactual = int((frequency * (1 << 23)) / (clock_frequency * scaling_factor))
    vactual = max(-(1 << 23), min((1 << 23) - 1, vactual))
    return vactual

def move_steps_over_time(camera_driver, start_position, end_position,
                         time_seconds, micro=128, ratio=None):
    steps = abs(end_position - start_position)

    if camera_driver:
        direction = -1 if end_position < start_position else 1
        time_seconds = time_seconds * 2
    else:
        direction = 1 if driver1.direction else -1

    if ratio is not None:
        steps = steps / ratio

    total_microsteps = steps * micro
    microsteps_per_second = total_microsteps / time_seconds
    fCLK = 12000000
    if camera_driver:
        vactual = int(microsteps_per_second / (fCLK / (1 << 24)))
    else:
        vactual = int(microsteps_per_second / (fCLK / (1 << 27)))
    velocity = max(-(1 << 23), min((1 << 23) - 1, vactual))
    velocity *= direction
    return velocity

def calculate_timelapse_velocity(start_position, end_position, duration_seconds, micro=128,
                                 clock_frequency=12000000, scaling_factor=6, min_velocity=100):
    total_steps = abs(end_position - start_position)
    steps_per_second = total_steps / duration_seconds
    full_steps_per_second = steps_per_second / micro
    vactual = calculate_linear_velocity(full_steps_per_second, clock_frequency,
                                        micro, scaling_factor)
    direction = -1 if end_position < start_position else 1
    if abs(vactual) < min_velocity and vactual != 0:
        vactual = min_velocity * direction
    return vactual

def calculate_rail_velocity(total_steps, duration_sec, direction,
                            is_timelapse=True, micro=128, clock_frequency=12000000):
    steps_per_second = total_steps / duration_sec
    full_steps_per_second = steps_per_second / micro
    if not is_timelapse:
        base_scaling = 1.0
        min_velocity = 400
        vactual = int((full_steps_per_second * micro * (1 << 23))
                      / (clock_frequency * base_scaling))
        vactual *= direction
        if abs(vactual) < min_velocity:
            vactual = min_velocity * direction
    else:
        base_scaling = 6.0
        min_velocity = 50
        vactual = int((full_steps_per_second * micro * (1 << 23)) /
                      (clock_frequency * base_scaling))
        vactual *= direction
        if abs(vactual) < min_velocity:
            vactual = min_velocity * direction
    vactual = max(-(1 << 23), min((1 << 23) - 1, vactual))
    return vactual

def move_motor_with_rotate(driver, movement_state, start_position=None,
                           end_position=None, duration_sec=0, micro=128):
    if start_position is not None and end_position is not None and not movement_state["is_active"]:
        if timelapse:
            driver.enable_motor(run_current=20)
            scaling_factor = 6
            min_velocity = 50
            velocity = calculate_timelapse_velocity(
                start_position,
                end_position,
                duration_sec,
                micro,
                scaling_factor=scaling_factor,
                min_velocity=min_velocity
            )
        else:
            driver.enable_motor(run_current=30)
            velocity = calculate_rail_velocity(
                    int(RAILS*STEPS_PER_MM),
                    duration_sec,
                    movement_state["step_direction"],
                    is_timelapse=timelapse,
                    micro=micro
                )
            initial_velocity = int(velocity * 0.2)
            if abs(initial_velocity) < 200:
                initial_velocity = 200 * (1 if velocity > 0 else -1)
            driver.rotate(initial_velocity)
            movement_state["initial_velocity"] = initial_velocity
            movement_state["final_velocity"] = velocity
            movement_state["ramp_up_done"] = False
            movement_state["ramp_up_time"] = 500
            movement_state["total_steps"] = int(RAILS*STEPS_PER_MM)
            movement_state["step_direction"] = 1 if end_position > start_position else -1
            movement_state["start_pos"] = 0
            movement_state["end_pos"] = int(RAILS*STEPS_PER_MM)
            movement_state["movement_start_time"] = supervisor.ticks_ms()
            movement_state["movement_duration_ms"] = duration_sec * 1000
            movement_state["is_active"] = True
            movement_state["is_paused"] = False
            return
        movement_state["total_steps"] = int(RAILS*STEPS_PER_MM)
        movement_state["step_direction"] = driver.direction
        movement_state["start_pos"] = 0
        movement_state["end_pos"] = int(RAILS*STEPS_PER_MM)

        if duration_sec > 0 and movement_state["total_steps"] > 0:
            movement_state["velocity"] = velocity
            driver.rotate(velocity)
            movement_state["movement_start_time"] = supervisor.ticks_ms()
            movement_state["movement_duration_ms"] = duration_sec * 1000
        else:
            default_velocity = 2000 * movement_state["step_direction"]
            driver.rotate(default_velocity)
            movement_state["movement_duration_ms"] = movement_state["total_steps"] * 10
            movement_state["movement_start_time"] = supervisor.ticks_ms()
        movement_state["is_active"] = True
        movement_state["is_paused"] = False

    if movement_state["is_active"] and movement_state["toggle_pause"]:
        movement_state["is_paused"] = not movement_state["is_paused"]
        movement_state["toggle_pause"] = False
        if movement_state["is_paused"]:
            driver.rotate(0)
            movement_state["pause_time"] = supervisor.ticks_ms()
        else:
            elapsed_ms = movement_state["pause_time"] - movement_state["movement_start_time"]
            remaining_ms = movement_state["movement_duration_ms"] - elapsed_ms
            if remaining_ms > 0:
                driver.rotate(movement_state["velocity"])
                movement_state["movement_start_time"] = supervisor.ticks_ms() - elapsed_ms
            else:
                driver.rotate(0)
                driver.disable_motor()
                movement_state["is_active"] = False

    if movement_state["is_active"] and movement_state["stop_requested"]:
        driver.rotate(0)
        driver.disable_motor()
        movement_state["is_active"] = False
        movement_state["stop_requested"] = False
        return {
            "active": False,
            "complete": False,
            "progress_percent": (supervisor.ticks_ms() - movement_state["movement_start_time"])
                                 / movement_state["movement_duration_ms"] * 100,
            "stopped_by_user": True
        }

    if movement_state["is_active"] and not movement_state["is_paused"]:
        current_t = supervisor.ticks_ms()
        e = current_t - movement_state["movement_start_time"]
        if e >= movement_state["movement_duration_ms"]:
            print("Movement time complete!")
            driver.rotate(0)
            driver.disable_motor()
            movement_state["is_active"] = False
            return {
                "active": False,
                "complete": True,
                "progress_percent": 100,
                "stopped_by_user": False
            }

    return {
        "active": movement_state["is_active"],
        "paused": movement_state["is_paused"],
        "progress_percent": (supervisor.ticks_ms() - movement_state["movement_start_time"]) /
                             movement_state["movement_duration_ms"] * 100
                            if movement_state["is_active"] else 0,
        "stopped_by_user": False
    }

def pause_resume_motor1():
    motor1_movement["toggle_pause"] = True

def stop_motor1():
    driver1.disable_motor()
    driver1.reset_position()
    motor1_movement["stop_requested"] = True

def pause_resume_motor2():
    motor2_movement["toggle_pause"] = True

def stop_motor2():
    driver2.disable_motor()
    driver2.reset_position()
    motor2_movement["stop_requested"] = True

def stop_all_motors():
    driver1.rotate(0)
    driver2.rotate(0)
    driver1.disable_motor()
    driver2.disable_motor()
    motor1_movement["is_active"] = False
    motor2_movement["is_active"] = False
    motor1_movement["stop_requested"] = False
    motor2_movement["stop_requested"] = False
    time.sleep(0.1)

driver1.disable_motor()
driver1.reset_position()
driver2.reset_position()

while True:
    if motor1_movement["is_active"]:
        current_time = supervisor.ticks_ms()
        elapsed = current_time - motor1_movement["movement_start_time"]
        if elapsed >= motor1_movement["movement_duration_ms"]:
            driver1.rotate(0)
            driver1.disable_motor()
            motor1_movement["is_active"] = False
    if motor2_movement["is_active"]:
        current_time = supervisor.ticks_ms()
        elapsed = current_time - motor2_movement["movement_start_time"]
        if elapsed >= motor2_movement["movement_duration_ms"]:
            driver2.rotate(0)
            driver2.disable_motor()
            motor2_movement["is_active"] = False
    if menu == 7:
        active_motors = 0
        progress1 = 0
        progress2 = 0
        if motor1_movement["is_active"]:
            active_motors += 1
            current_time = supervisor.ticks_ms()
            elapsed = current_time - motor1_movement["movement_start_time"]
            progress1 = (elapsed / motor1_movement["movement_duration_ms"]) * 100
        if motor2_movement["is_active"]:
            active_motors += 1
            current_time = supervisor.ticks_ms()
            elapsed = current_time - motor2_movement["movement_start_time"]
            progress2 = (elapsed / motor2_movement["movement_duration_ms"]) * 100
        if active_motors > 0:
            avg_progress = (progress1 + progress2) / active_motors
            text_area.text = f"{running_text[select]} {avg_progress:.1f}%"
            display.refresh()
        elif active_motors == 0 and (motor1_movement["movement_duration_ms"] > 0
                                     or motor2_movement["movement_duration_ms"] > 0):
            text_area.text = "Movement Complete!"
            display.refresh()
    event = keys.events.get()
    if event:
        if event.pressed:
            print(f"{event.key_number} pressed")
            if event.key_number == 0:
                if menu == 0:
                    menu = adv_menu(menu)
                elif menu == 2:
                    if select == 0:
                        motor2_coordinates[select] = driver2.position
                    if select == 1:
                        motor2_coordinates[select] = driver2.position
                    select += 1
                    text_area.text = motor2_text[select]
                    if select > 1:
                        select = 0
                        menu = adv_menu(menu)
                        if motor2_coordinates[0] > motor2_coordinates[1]:
                            move = motor2_coordinates[0] - motor2_coordinates[1]
                        else:
                            move = motor2_coordinates[1] - motor2_coordinates[0]
                            move = -move
                        driver2.step(move)
                elif menu == 3:
                    if select == 1:
                        timelapse = False
                        menu += 1
                        select = 0
                    else:
                        timelapse = True
                    menu = adv_menu(menu)
                elif menu == 4:
                    menu += 1
                    time_mode = select
                    menu = adv_menu(menu)
                    select = 0
                    print(f"{time_text[time_mode]}, timelapse: {timelapse}")
                elif menu == 5:
                    shot_mode = select
                    menu = adv_menu(menu)
                    select = 0
                    print(f"{shot_text[shot_mode]}, timelapse: {timelapse}")
                elif menu == 6:
                    menu = adv_menu(menu)
                    if timelapse:
                        movement_time = int(time_text[time_mode]) * 60
                        print(f"starting a timelapse for {time_text[time_mode]} minutes")
                        status1 = move_motor_with_rotate(
                            driver1,
                            motor1_movement,
                            start_position=0,
                            end_position=int(RAILS * STEPS_PER_MM),
                            duration_sec=movement_time,
                            microsteps=microsteps
                        )
                        if abs(motor2_coordinates[1] - motor2_coordinates[0]) > 0:
                            velocity2 = move_steps_over_time(camera_driver=True,
                                                             start_position=motor2_coordinates[0],
                                                             end_position=motor2_coordinates[1],
                                                             time_seconds=movement_time,
                                                             microsteps=microsteps,
                                                             ratio=gear_ratio)
                            print(f"driver2 velocity is: {velocity2}")
                            driver2.enable_motor(run_current=25)
                            driver2.rotate(velocity2)
                            motor2_movement["is_active"] = True
                            motor2_movement["start_pos"] = motor2_coordinates[0]
                            motor2_movement["end_pos"] = motor2_coordinates[1]
                            motor2_movement["movement_start_time"] = supervisor.ticks_ms()
                            motor2_movement["movement_duration_ms"] = movement_time * 1000
                            motor2_movement["velocity"] = velocity2
                            motor2_movement["total_steps"] = (abs(motor2_coordinates[1] -
                                                                  motor2_coordinates[0]))
                    else:
                        print(f"starting a {shot_text[shot_mode]} one-shot")
                        movement_time = shot_velocities[shot_mode]
                        status1 = move_motor_with_rotate(
                            driver1,
                            motor1_movement,
                            start_position=0,
                            end_position=int(RAILS * STEPS_PER_MM),
                            duration_sec=movement_time,
                            microsteps=microsteps
                        )
                        if abs(motor2_coordinates[1] - motor2_coordinates[0]) > 0:
                            velocity2 = move_steps_over_time(camera_driver=True,
                                                             start_position=motor2_coordinates[0],
                                                             end_position=motor2_coordinates[1],
                                                             time_seconds=movement_time,
                                                             microsteps=microsteps,
                                                             ratio=gear_ratio)
                            driver2.enable_motor(run_current=25)
                            driver2.rotate(velocity2)
                            motor2_movement["is_active"] = True
                            motor2_movement["start_pos"] = motor2_coordinates[0]
                            motor2_movement["end_pos"] = motor2_coordinates[1]
                            motor2_movement["movement_start_time"] = supervisor.ticks_ms()
                            motor2_movement["movement_duration_ms"] = movement_time * 1000
                            motor2_movement["velocity"] = velocity2
                            motor2_movement["total_steps"] = (abs(motor2_coordinates[1] -
                                                                  motor2_coordinates[0]))
                elif menu == 7:
                    if select == 0:
                        stop_all_motors()
                        text_area.text = "Stopping..."
                        menu = adv_menu(menu)
                    elif select == 1:
                        pause_resume_motor1()
                        pause_resume_motor2()
                        paused_state = motor1_movement["is_paused"] or motor2_movement["is_paused"]
                        text_area.text = "Paused" if paused_state else "Running"
                    display.refresh()
            if event.key_number == 1:
                if menu == 1:
                    driver1.direction = False
                    driver1.reset_position()
                    menu = adv_menu(menu)
                elif menu == 7:
                    stop_all_motors()
                    menu = adv_menu(menu)
            if event.key_number == 2:
                if menu == 1:
                    driver1.direction = True
                    driver1.reset_position()
                    menu = adv_menu(menu)
                elif menu == 7:
                    stop_all_motors()
                    menu = adv_menu(menu)
        display.refresh()
    pos = encoder.position
    if pos != last_pos:
        if pos > last_pos:
            if menu == 2:
                driver2.step(-10)
            if menu == 3:
                select = (select + 1) % 2
                text_area.text = mode_text[select]
                grid_bg[0] = mode_icons[select]
            if menu == 4:
                select = (select + 1) % len(time_text)
                text_area.text = time_text[select]
            if menu == 5:
                select = (select + 1) % len(shot_text)
                text_area.text = shot_text[select]
            if menu == 7:
                select = (select + 1) % len(running_text)
                text_area.text = running_text[select]
                grid_bg[0] = running_icons[select]
        else:
            if menu == 2:
                driver2.step(10)
            if menu == 3:
                select = (select - 1) % 2
                text_area.text = mode_text[select]
                grid_bg[0] = mode_icons[select]
            if menu == 4:
                select = (select - 1) % len(time_text)
                text_area.text = time_text[select]
            if menu == 5:
                select = (select - 1) % len(shot_text)
                text_area.text = shot_text[select]
            if menu == 7:
                select = (select - 1) % len(running_text)
                text_area.text = running_text[select]
                grid_bg[0] = running_icons[select]
        last_pos = pos
        display.refresh()
