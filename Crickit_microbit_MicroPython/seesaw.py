# Adafruit Seesaw / CRICKIT driver for MicroPython
# MIT License by Adafruit Industries Limor Fried
# Copy onto the micro:bit with main.py using Mu Files icon
from microbit import i2c
import struct
import time

_SIGNALS = (2, 3, 40, 41, 11, 10, 9, 8)
_PWMS = (14, 15, 16, 17, 19, 18, 22, 23, 42, 43, 12, 13)
_SERVOS = (17, 16, 15, 14)
_MOTORS = (22, 23, 19, 18)
_DRIVES = (13, 12, 43, 42)
_TOUCHES = (0, 1, 2, 3)
_ADDR = 0x49

reg_buf = bytearray(2)
pwm_buf = bytearray(3)

def _read(reghi, reglo, n, delay_s=0.01):
    reg_buf[0] = reghi
    reg_buf[1] = reglo
    i2c.write(_ADDR, reg_buf)
    time.sleep(delay_s)
    return i2c.read(_ADDR, n)

def _write(reghi, reglo, cmd):
    reg_buf[0] = reghi
    reg_buf[1] = reglo
    #print("sswrite: ", [hex(i) for i in reg_buf+cmd])
    i2c.write(_ADDR, reg_buf+cmd)

# t is between 1 and 4
def read_touch(t):
    return struct.unpack(">H", _read(0x0F, 0x10+_TOUCHES[t-1], 2))[0]

def pwm_write(pwm, val):
    pwm_buf[0] = _PWMS.index(pwm)
    pwm_buf[1] = val >> 8
    pwm_buf[2] = val & 0xFF
    _write(0x08, 0x01, pwm_buf)

def set_pwmfreq(pwm, freq):
    pwm_buf[0] = _PWMS.index(pwm)
    pwm_buf[1] = freq >> 8
    pwm_buf[2] = freq & 0xFF
    _write(0x08, 0x02, pwm_buf)

# signal is between 1 and 8
def analog_read(signal):
    return struct.unpack(">H", _read(0x09, 0x07+signal-1, 2))[0]

def pin_config(pin, mode, pull=None, val=None):
    if pin >= 32:
        cmd = struct.pack(">I", 1 << (pin - 32))
        cmd = bytearray(4) + cmd
    else:
        cmd = struct.pack(">I", 1 << pin)
    if 0 <= mode <= 1:
        _write(0x01, 0x03-mode, cmd)
    if pull is not None and 0 <= pull <= 1:
        _write(0x01, 0x0C-pull, cmd)
    if val is not None and 0 <= val <= 1:
        _write(0x01, 0x06-val, cmd)


def init():
    i2c.init()
    while not _ADDR in i2c.scan():
        print("Crickit not found!")
        time.sleep(1)
    reg_buf[0] = 0x7F
    reg_buf[1] = 0xFF
    i2c.write(_ADDR, reg_buf)

# s is between 1 and 4
def servo(s, degree, min=1.0, max=2.0):
    set_pwmfreq(_SERVOS[s-1], 50)
    val = 3276*min + (max-min)*3276*degree/180
    pwm_write(_SERVOS[s-1], int(val))

# d is between 1 and 4
def drive(d, frac, freq=1000):
    set_pwmfreq(_DRIVES[d-1], freq)
    pwm_write(_DRIVES[d-1], int(frac*65535))

# m is 1 or 2
def motor(m, frac, freq=1000):
    m -= 1  # start with 1
    pin1,pin2 = _MOTORS[m*2:m*2+2]
    set_pwmfreq(pin1, freq)
    set_pwmfreq(pin2, freq)
    if frac < 0:
        pin1, pin2 = pin2, pin1
    pwm_write(pin1, 0)
    pwm_write(pin2, abs(int(frac*65535)))

# signal is between 1 and 8, val is 0 or 1
def write_digital(signal, val):
    pin_config(_SIGNALS[signal-1], 1, 0, val) # output, pullup, value

# signal is between 1 and 8
def read_digital(signal):
    pin = _SIGNALS[signal-1]
    pin_config(pin, 0, 1, 1) # input, pullup, pullvalue
    ret = _read(0x01, 0x04, 8)
    b = 0
    if pin > 32:
        b = 4
        pin -= 32
    b += 3 - (pin // 8)
    return (ret[b] & 1<<(pin % 8)) != 0
