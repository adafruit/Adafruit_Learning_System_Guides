# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import busio
from micropython import const
from generic_uart_device import GenericUARTDevice

# pylint: disable=protected-access, too-many-public-methods, bare-except, too-many-function-args

class TMC2209:

    GCONF        = const(0x00)  # Global configuration
    GSTAT        = const(0x01)  # Global status flags
    IFCNT        = const(0x02)  # Interface transmission counter
    NODECONF     = const(0x03)  # Node configuration
    OTP_PROG     = const(0x04)  # OTP programming
    OTP_READ     = const(0x05)  # OTP read data
    IOIN         = const(0x06)
    FACTORY_CONF = const(0x07)  # Factory configuration

    # Velocity Dependent Control Registers
    IHOLD_IRUN   = const(0x10)
    TPOWERDOWN   = const(0x11)  # Power down delay
    TSTEP        = const(0x12)  # Time between steps
    TPWMTHRS     = const(0x13)  # Upper velocity for StealthChop
    TCOOLTHRS    = const(0x14)  # Lower threshold velocity for CoolStep
    VACTUAL      = const(0x22)

    # StallGuard Control Registers
    SGTHRS       = const(0x40)  # StallGuard threshold
    SG_RESULT    = const(0x41)  # StallGuard result
    COOLCONF     = const(0x42)  # CoolStep configuration

    # Sequencer Registers
    MSCNT        = const(0x6A)
    MSCURACT     = const(0x6B)

    # Chopper Control Registers
    DRV_STATUS   = const(0x6F)  # Driver status
    PWMCONF      = const(0x70)  # StealthChop PWM config
    PWM_SCALE    = const(0x71)  # PWM scaling values
    PWM_AUTO     = const(0x72)  # PWM automatic configuration

    CHOPCONF     = const(0x6C)
    MRES_START     = 24  # Microstepping resolution bits start position
    MRES_LENGTH    = 4   # Number of bits for microstepping resolution

    # GCONF register bit positions
    GCONF_I_SCALE_ANALOG    = const(0)
    GCONF_INTERNAL_RSENSE   = const(1)
    GCONF_EN_SPREADCYCLE    = const(2)
    GCONF_SHAFT             = const(3)
    GCONF_INDEX_OTPW        = const(4)
    GCONF_INDEX_STEP        = const(5)
    GCONF_PDN_DISABLE       = const(6)
    GCONF_MSTEP_REG_SELECT  = const(7)
    GCONF_MULTISTEP_FILT    = const(8)
    GCONF_TEST_MODE         = const(9)

    # GSTAT register bit positions
    GSTAT_RESET             = const(0)
    GSTAT_DRV_ERR           = const(1)
    GSTAT_UV_CP             = const(2)

    # CHOPCONF register bit positions
    CHOPCONF_TOFF_START     = const(0)
    CHOPCONF_HSTRT_START    = const(4)
    CHOPCONF_HEND_START     = const(7)
    CHOPCONF_TBL_START      = const(15)
    CHOPCONF_VSENSE         = const(17)
    CHOPCONF_MRES_START     = const(24)
    CHOPCONF_INTPOL         = const(28)
    CHOPCONF_DEDGE          = const(29)
    CHOPCONF_DISS2G         = const(30)
    CHOPCONF_DISS2VS        = const(31)

    # PWMCONF register bit positions
    PWMCONF_PWM_OFS         = const(0)
    PWMCONF_PWM_GRAD        = const(8)
    PWMCONF_PWM_FREQ        = const(16)
    PWMCONF_PWM_AUTOSCALE   = const(18)
    PWMCONF_PWM_AUTOGRAD    = const(19)
    PWMCONF_FREEWHEEL       = const(20)
    PWMCONF_PWM_REG         = const(24)
    PWMCONF_PWM_LIM         = const(28)

    # DRV_STATUS bit positions
    DRV_STATUS_OTPW         = const(0)
    DRV_STATUS_OT           = const(1)
    DRV_STATUS_S2GA         = const(2)
    DRV_STATUS_S2GB         = const(3)
    DRV_STATUS_S2VSA        = const(4)
    DRV_STATUS_S2VSB        = const(5)
    DRV_STATUS_OLA          = const(6)
    DRV_STATUS_OLB          = const(7)
    DRV_STATUS_T120         = const(8)
    DRV_STATUS_T143         = const(9)
    DRV_STATUS_T150         = const(10)
    DRV_STATUS_T157         = const(11)
    DRV_STATUS_CS_ACTUAL    = const(16)  # Start bit for CS_ACTUAL
    DRV_STATUS_STEALTH      = const(30)
    DRV_STATUS_STST         = const(31)

    # COOLCONF register bit positions
    COOLCONF_SEMIN          = const(0)
    COOLCONF_SEUP           = const(5)
    COOLCONF_SEMAX          = const(8)
    COOLCONF_SEDN           = const(13)
    COOLCONF_SEIMIN         = const(15)

    def __init__(self, uart=None, tx_pin=None, rx_pin=None, addr=0, baudrate=115200):

        if uart is None and tx_pin is not None and rx_pin is not None:
            uart = busio.UART(tx=tx_pin, rx=rx_pin, baudrate=baudrate, timeout=0.1)
        elif uart is None:
            raise ValueError("Either uart or tx_pin and rx_pin must be provided")

        self._addr = addr & 0x03

        self._device = GenericUARTDevice(
            uart=uart,
            read_func=self._uart_read,
            write_func=self._uart_write,
            readreg_func=self.read_reg,
            writereg_func=self.write_reg
        )
        gconf = self.read_reg(self.GCONF)
        gconf |= (1 << 7)
        self.write_reg(self.GCONF, gconf)
        ihold_irun = (
            (16 << 0) |   # IHOLD = 16 (50% of max current)
            (31 << 8) |   # IRUN = 31 (max current)
            (1 << 16)     # IHOLDDELAY = 1
        )
        self.write_reg(self.IHOLD_IRUN, ihold_irun)

        self._step_count = 0  # Track full steps
        self._last_mscnt = self.mscnt  # Initialize last microstep counter
        self._step_count = 0
        self._last_mscnt = 0
        try:
            self._last_mscnt = self.mscnt
        except:
            pass
        self._start_position = None
        self._end_position = None

    @staticmethod
    def calc_crc(data: bytes) -> int:
        """Calculate CRC8-ATM
        Polynomial: x^8 + x^2 + x + 1 (0x07)
        """
        crc = 0
        for byte in data:
            for _ in range(8):
                if (crc >> 7) ^ (byte & 0x01):
                    crc = ((crc << 1) ^ 0x07) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
                byte = byte >> 1
        return crc

    def read_reg(self, reg_addr: int) -> int:
        """Read a register value"""
        while self._device._uart.in_waiting:
            self._device._uart.read()
        datagram = bytes([
            0x05,
            self._addr << 1,
            reg_addr,
            0x00
        ])
        datagram = datagram[:-1] + bytes([self.calc_crc(datagram[:-1])])
        self._device._uart.write(datagram)
        echo = bytearray(4)
        if not self._device._uart.readinto(echo):
            return 0
        response = bytearray(8)
        if not self._device._uart.readinto(response):
            return 0
        value = (response[3] << 24) | (response[4] << 16) | (response[5] << 8) | response[6]
        return value

    def write_reg(self, reg_addr: int, value: int):
        """Write a value to a register"""
        if value < 0:
            value = value & 0xFFFFFFFF
        while self._device._uart.in_waiting:
            self._device._uart.read()
        data = value.to_bytes(4, 'big', signed=False)
        datagram = bytes([
            0x05,
            self._addr << 1,
            reg_addr | 0x80,
            data[0],
            data[1],
            data[2],
            data[3],
            0x00
        ])
        datagram = datagram[:-1] + bytes([self.calc_crc(datagram[:-1])])
        self._device._uart.write(datagram)
        echo = bytearray(8)
        self._device._uart.readinto(echo)

    def _uart_read(self, buffer: bytearray) -> int:
        """Read raw data from UART"""
        return self._device._uart.readinto(buffer)

    def _uart_write(self, buffer: bytes) -> int:
        """Write raw data to UART"""
        return self._device._uart.write(buffer)

    @property
    def mscnt(self) -> int:
        """Read the microstep counter
        Returns the current position in the microstep table (0-1023)
        """
        return self.read_reg(self.MSCNT) & 0x3FF  # 10-bit value (0-1023)

    @property
    def mscuract(self) -> tuple:
        """Read the current microstep current for both phases
        Returns:
            tuple: (CUR_A, CUR_B) - Current for phase A and B (-255 to 255)
        """
        value = self.read_reg(self.MSCURACT)
        cur_a = (value >> 16) & 0x1FF
        cur_b = value & 0x1FF
        if cur_a & 0x100:
            cur_a = -(cur_a ^ 0x1FF) - 1
        if cur_b & 0x100:
            cur_b = -(cur_b ^ 0x1FF) - 1
        return (cur_a, cur_b)

    @property
    def position(self) -> float:
        """Get the current motor position in steps
        This combines full steps tracked by software and microsteps from the driver
        """
        return self._step_count

    def reset_position(self):
        """Reset the position counter to zero at the current position"""
        self._step_count = 0
        self._last_mscnt = self.mscnt

    @property
    def version(self) -> int:
        """Read chip version"""
        ioin = self.read_reg(self.IOIN)
        return (ioin >> 24) & 0xFF

    @property
    def microsteps(self) -> int:
        """Get current microsteps (1-256)"""
        chopconf = self.read_reg(self.CHOPCONF)
        mres = (chopconf >> self.MRES_START) & ((1 << self.MRES_LENGTH) - 1)
        return 256 >> mres if mres <= 8 else 0

    @microsteps.setter
    def microsteps(self, steps: int):
        """Set microsteps (1-256, will be rounded to power of 2)"""
        steps = min(256, max(1, steps))
        mres = 0
        while steps < 256:
            steps = steps << 1
            mres += 1

        chopconf = self.read_reg(self.CHOPCONF)
        mask = ((1 << self.MRES_LENGTH) - 1) << self.MRES_START
        chopconf = (chopconf & ~mask) | ((mres & 0xF) << self.MRES_START)

        self.write_reg(self.CHOPCONF, chopconf)

    @property
    def direction(self) -> bool:
        """Get current direction (True = reversed, False = normal)"""
        gconf = self.read_reg(self.GCONF)
        return bool(gconf & (1 << 3))

    @direction.setter
    def direction(self, reverse: bool):
        """Set motor direction (True = reversed, False = normal)"""
        gconf = self.read_reg(self.GCONF)
        if reverse:
            gconf |= (1 << 3)
        else:
            gconf &= ~(1 << 3)
        self.write_reg(self.GCONF, gconf)

    def rotate(self, velocity: int):
        """Rotate the motor at a specific velocity
        Args:
            velocity: Rotation velocity (-2^23 to +2^23)
                    Positive for forward, negative for reverse
        """
        # Clamp velocity to valid range (-2^23 to 2^23 - 1)
        velocity = max(-(1 << 23), min((1 << 23) - 1, velocity))
        self.write_reg(self.VACTUAL, velocity)

    def step(self, steps: int, delay: float = 0.001):
        """Step the motor a specific number of steps
        Args:
            steps: Number of steps (negative for reverse direction)
            delay: Delay between steps in seconds
        """
        direction = 1 if steps > 0 else -1
        for _ in range(abs(steps)):
            self.rotate(10000 * direction)
            time.sleep(delay)
            self.stop()
            # Update position counter
            self._step_count += direction

    def stop(self):
        """Stop the motor"""
        self.write_reg(self.VACTUAL, 0)

    def set_current(self, run_current: int, hold_current: int = None):
        """Set motor current

        Args:
            run_current: Running current (0-31)
            hold_current: Holding current (0-31), defaults to 50% of run_current
        """
        if hold_current is None:
            hold_current = run_current // 2

        run_current = min(31, max(0, run_current))
        hold_current = min(31, max(0, hold_current))

        ihold_irun = (
            (hold_current << 0) |   # IHOLD
            (run_current << 8) |    # IRUN
            (1 << 16)              # IHOLDDELAY
        )
        self.write_reg(self.IHOLD_IRUN, ihold_irun)

    @property
    def stealth_chop_enabled(self):
        """Check if StealthChop mode is enabled

        Returns:
            bool: True if StealthChop is enabled, False if SpreadCycle is active
        """
        gconf = self.read_reg(self.GCONF)
        return not bool(gconf & (1 << self.GCONF_EN_SPREADCYCLE))

    @stealth_chop_enabled.setter
    def stealth_chop_enabled(self, enable):
        """Enable or disable StealthChop mode (voltage PWM mode)

        Args:
            enable (bool): True to enable StealthChop, False to use SpreadCycle
        """
        gconf = self.read_reg(self.GCONF)
        if enable:
            # Clear EN_SPREADCYCLE bit to enable StealthChop
            gconf &= ~(1 << self.GCONF_EN_SPREADCYCLE)
        else:
            # Set EN_SPREADCYCLE bit to enable SpreadCycle mode
            gconf |= (1 << self.GCONF_EN_SPREADCYCLE)
        self.write_reg(self.GCONF, gconf)

    @property
    def pwm_threshold(self):
        """Get the TSTEP threshold for switching to StealthChop

        Returns:
            int: Current TSTEP threshold value
        """
        return self.read_reg(self.TPWMTHRS)

    @pwm_threshold.setter
    def pwm_threshold(self, threshold):
        """Set the TSTEP threshold for switching to StealthChop

        This sets the upper velocity threshold for StealthChop operation.
        When TSTEP falls below this value (higher velocity), the driver
        will switch from StealthChop to SpreadCycle.

        Args:
            threshold (int): TSTEP threshold value (0-1048575)
                            0 = Disabled (use SpreadCycle only)
        """
        # Clamp threshold to valid range
        threshold = max(0, min(threshold, (1 << 20) - 1))
        self.write_reg(self.TPWMTHRS, threshold)

    @property
    def pwm_scale(self):
        """Read the PWM scaling values (results of StealthChop amplitude regulator)

        Returns:
            tuple: (PWM_SCALE_SUM, PWM_SCALE_AUTO) where:
                PWM_SCALE_SUM (0-255): Actual PWM duty cycle
                PWM_SCALE_AUTO (-255 to +255): Signed offset from automatic amplitude regulation
        """
        pwm_scale = self.read_reg(self.PWM_SCALE)
        pwm_scale_sum = pwm_scale & 0xFF
        pwm_scale_auto = (pwm_scale >> 16) & 0x1FF
        if pwm_scale_auto & 0x100:
            pwm_scale_auto = -(pwm_scale_auto ^ 0x1FF) - 1
        return (pwm_scale_sum, pwm_scale_auto)

    @property
    def pwm_auto(self):
        """Read the automatically generated PWM configuration values

        These values can be used as defaults for future configurations.

        Returns:
            tuple: (PWM_OFS_AUTO, PWM_GRAD_AUTO) where:
                PWM_OFS_AUTO (0-255): Automatically determined offset value
                PWM_GRAD_AUTO (0-255): Automatically determined gradient value
        """
        pwm_auto = self.read_reg(self.PWM_AUTO)
        pwm_ofs_auto = pwm_auto & 0xFF
        pwm_grad_auto = (pwm_auto >> 16) & 0xFF

        return (pwm_ofs_auto, pwm_grad_auto)

    def set_pwm_config(self,
                    pwm_offset=36,     # PWM amplitude offset
                    pwm_gradient=0,    # PWM amplitude gradient
                    pwm_freq=1,        # PWM frequency setting
                    pwm_autoscale=True, # Automatic amplitude scaling
                    pwm_autograd=True,  # Automatic gradient adaptation
                    freewheel_mode=0,   # Standstill mode
                    pwm_reg=4,          # Regulation loop gradient
                    pwm_lim=12):        # PWM scale limit
        """Configure StealthChop PWM mode parameters

        Args:
            pwm_offset (int): PWM amplitude offset (0-255)
            pwm_gradient (int): PWM amplitude gradient (0-255)
            pwm_freq (int): PWM frequency selection (0-3)
                0: fPWM=2/1024 fCLK
                1: fPWM=2/683 fCLK
                2: fPWM=2/512 fCLK
                3: fPWM=2/410 fCLK
            pwm_autoscale (bool): Enable automatic current scaling
            pwm_autograd (bool): Enable automatic gradient adaptation
            freewheel_mode (int): Standstill mode when motor current is 0 (0-3)
                0: Normal operation
                1: Freewheeling
                2: Coil shorted using LS drivers
                3: Coil shorted using HS drivers
            pwm_reg (int): Regulation loop gradient (1-15)
            pwm_lim (int): PWM automatic scale amplitude limit (0-15)
        """
        pwm_offset = max(0, min(pwm_offset, 255))
        pwm_gradient = max(0, min(pwm_gradient, 255))
        pwm_freq = max(0, min(pwm_freq, 3))
        freewheel_mode = max(0, min(freewheel_mode, 3))
        pwm_reg = max(1, min(pwm_reg, 15))
        pwm_lim = max(0, min(pwm_lim, 15))
        pwmconf = (
            (pwm_lim & 0x0F) << self.PWMCONF_PWM_LIM |
            (pwm_reg & 0x0F) << self.PWMCONF_PWM_REG |
            (freewheel_mode & 0x03) << self.PWMCONF_FREEWHEEL |
            (int(pwm_autograd) & 0x01) << self.PWMCONF_PWM_AUTOGRAD |
            (int(pwm_autoscale) & 0x01) << self.PWMCONF_PWM_AUTOSCALE |
            (pwm_freq & 0x03) << self.PWMCONF_PWM_FREQ |
            (pwm_gradient & 0xFF) << self.PWMCONF_PWM_GRAD |
            (pwm_offset & 0xFF) << self.PWMCONF_PWM_OFS
        )

        self.write_reg(self.PWMCONF, pwmconf)

    @property
    def stall_threshold(self):
        """Get the StallGuard threshold for stall detection

        Returns:
            int: StallGuard threshold value (0-255)
                Lower values = more sensitive
        """
        return self.read_reg(self.SGTHRS)

    @stall_threshold.setter
    def stall_threshold(self, threshold):
        """Set the StallGuard threshold for stall detection

        Args:
            threshold (int): StallGuard threshold value (0-255)
                            Lower values = more sensitive stall detection
        """
        # Clamp threshold to valid range
        threshold = max(0, min(threshold, 255))
        self.write_reg(self.SGTHRS, threshold & 0xFF)

    @property
    def stall_guard_result(self):
        """Read the current StallGuard result

        Returns:
            int: StallGuard value (0-1023), higher = less motor load
                A value of 0 typically indicates a stalled motor
        """
        return self.read_reg(self.SG_RESULT)

    @property
    def coolstep_threshold(self):
        """Get the TSTEP threshold for enabling CoolStep and StallGuard

        Returns:
            int: TSTEP threshold value (0-1048575)
        """
        return self.read_reg(self.TCOOLTHRS)

    @coolstep_threshold.setter
    def coolstep_threshold(self, threshold):
        """Set the TSTEP threshold for enabling CoolStep and StallGuard

        When TSTEP is between TCOOLTHRS and TPWMTHRS:
        - StallGuard output signal becomes enabled
        - CoolStep becomes enabled (if configured)

        Args:
            threshold (int): TSTEP threshold value (0-1048575)
                            0 = Disabled
        """
        threshold = max(0, min(threshold, (1 << 20) - 1))
        self.write_reg(self.TCOOLTHRS, threshold)

    def configure_coolstep(self,
                        semin=0,          # Minimum StallGuard value (0-15)
                        semax=0,          # StallGuard hysteresis (0-15)
                        sedn=0,           # Current down step speed (0-3)
                        seup=0,           # Current up step width (0-3)
                        seimin=False):    # Minimum current setting
        """Configure CoolStep adaptive current scaling

        Args:
            semin (int): Minimum StallGuard value for smart current control (0-15)
                        0 = CoolStep disabled
            semax (int): StallGuard hysteresis value (0-15)
            sedn (int): Current down step speed (0-3)
                    0: Slowest (for each 32 StallGuard values)
                    1: Down step for each 8 StallGuard values
                    2: Down step for each 2 StallGuard values
                    3: Down step for each StallGuard value
            seup (int): Current up step width (0-3)
                    0: 1 step per measurement
                    1: 2 steps per measurement
                    2: 4 steps per measurement
                    3: 8 steps per measurement
            seimin (bool): Minimum current setting
                        False = 1/2 of current setting (IRUN)
                        True = 1/4 of current setting (IRUN)
        """
        semin = max(0, min(semin, 15))
        semax = max(0, min(semax, 15))
        sedn = max(0, min(sedn, 3))
        seup = max(0, min(seup, 3))

        coolconf = (
            (int(seimin) & 0x01) << self.COOLCONF_SEIMIN |
            (sedn & 0x03) << self.COOLCONF_SEDN |
            (semax & 0x0F) << self.COOLCONF_SEMAX |
            (seup & 0x03) << self.COOLCONF_SEUP |
            (semin & 0x0F) << self.COOLCONF_SEMIN
        )

        self.write_reg(self.COOLCONF, coolconf)

    def is_stalled(self):
        """Check if the motor has stalled based on StallGuard threshold

        Note: TCOOLTHRS must be set and StallGuard must be active
            (stepper must be moving at a speed where TSTEP > TCOOLTHRS)

        Returns:
            bool: True if motor is stalled, False otherwise
        """
        if self.coolstep_threshold == 0:
            return False
        sg_result = self.stall_guard_result
        threshold = self.stall_threshold * 2
        return sg_result <= threshold

    def get_temperature_status(self):
        """Get the current temperature status of the driver

        Returns:
            dict: Temperature flags
                'warning': True if temperature warning is active
                'shutdown': True if overtemperature shutdown is active
                't120': True if temperature exceeds 120°C
                't143': True if temperature exceeds 143°C
                't150': True if temperature exceeds 150°C
                't157': True if temperature exceeds 157°C
        """
        status = self.read_reg(self.DRV_STATUS)

        return {
            'warning': bool(status & (1 << self.DRV_STATUS_OTPW)),
            'shutdown': bool(status & (1 << self.DRV_STATUS_OT)),
            't120': bool(status & (1 << self.DRV_STATUS_T120)),
            't143': bool(status & (1 << self.DRV_STATUS_T143)),
            't150': bool(status & (1 << self.DRV_STATUS_T150)),
            't157': bool(status & (1 << self.DRV_STATUS_T157))
        }

    @property
    def driver_status(self):
        """Read driver status flags

        Returns:
            dict: Dictionary with status flags including:
                - standstill: Motor standstill detected
                - stealth_mode: Driver is in StealthChop mode
                - overtemperature_warning: Temperature warning flag
                - overtemperature_shutdown: Overtemperature shutdown flag
                - short_to_ground: Short to ground detected
                - low_side_short: Short on low side detected
                - open_load: Open load detected
                - temperature: Temperature status flags
                - current_scaling: Actual current scaling value
        """
        status = self.read_reg(self.DRV_STATUS)

        return {
            'standstill': bool(status & (1 << self.DRV_STATUS_STST)),
            'stealth_mode': bool(status & (1 << self.DRV_STATUS_STEALTH)),
            'overtemperature_warning': bool(status & (1 << self.DRV_STATUS_OTPW)),
            'overtemperature_shutdown': bool(status & (1 << self.DRV_STATUS_OT)),
            'short_to_ground': bool(status & ((1 << self.DRV_STATUS_S2GA) |
                                              (1 << self.DRV_STATUS_S2GB))),
            'low_side_short': bool(status & ((1 << self.DRV_STATUS_S2VSA) |
                                             (1 << self.DRV_STATUS_S2VSB))),
            'open_load': bool(status & ((1 << self.DRV_STATUS_OLA) | (1 << self.DRV_STATUS_OLB))),
            'temperature': {
                't120': bool(status & (1 << self.DRV_STATUS_T120)),
                't143': bool(status & (1 << self.DRV_STATUS_T143)),
                't150': bool(status & (1 << self.DRV_STATUS_T150)),
                't157': bool(status & (1 << self.DRV_STATUS_T157))
            },
            'current_scaling': (status >> self.DRV_STATUS_CS_ACTUAL) & 0x1F
        }

    @property
    def global_status(self):
        """Read global status flags

        Returns:
            dict: Dictionary with global status flags:
                - reset: Indicates IC has been reset
                - driver_error: Driver has been shut down due to error
                - undervoltage: Undervoltage on charge pump
        """
        gstat = self.read_reg(self.GSTAT)

        return {
            'reset': bool(gstat & (1 << self.GSTAT_RESET)),
            'driver_error': bool(gstat & (1 << self.GSTAT_DRV_ERR)),
            'undervoltage': bool(gstat & (1 << self.GSTAT_UV_CP))
        }

    def clear_error_flags(self):
        """Clear all error flags in GSTAT register

        This clears the reset, driver_error and undervoltage flags.
        """
        # Write 1 to each bit to clear the flags
        self.write_reg(self.GSTAT, 0x07)  # 0b111

    def interface_transmission_counter(self):
        """Read the interface transmission counter

        This counter is incremented with each successful UART write access.
        It can be used to verify that the UART communication is working correctly.

        Returns:
            int: Number of successful UART transmissions (0-255)
        """
        return self.read_reg(self.IFCNT)

    def set_freewheel_mode(self, mode):
        """Set the freewheel mode for when motor current is 0

        Args:
            mode (int): Freewheel mode (0-3)
                0: Normal operation
                1: Freewheeling (motor can spin freely)
                2: Coil shorted using LS drivers (passive braking)
                3: Coil shorted using HS drivers
        """
        mode = max(0, min(mode, 3))
        pwmconf = self.read_reg(self.PWMCONF)
        pwmconf &= ~(0x03 << self.PWMCONF_FREEWHEEL)
        pwmconf |= (mode & 0x03) << self.PWMCONF_FREEWHEEL
        self.write_reg(self.PWMCONF, pwmconf)

    def set_pwm_frequency(self, freq):
        """Set PWM frequency for StealthChop mode

        Args:
            freq (int): PWM frequency selection (0-3)
                0: fPWM=2/1024 fCLK (~23kHz @ 12MHz clock)
                1: fPWM=2/683 fCLK (~35kHz @ 12MHz clock)
                2: fPWM=2/512 fCLK (~47kHz @ 12MHz clock)
                3: fPWM=2/410 fCLK (~58kHz @ 12MHz clock)
        """
        freq = max(0, min(freq, 3))
        pwmconf = self.read_reg(self.PWMCONF)
        pwmconf &= ~(0x03 << self.PWMCONF_PWM_FREQ)
        pwmconf |= (freq & 0x03) << self.PWMCONF_PWM_FREQ
        self.write_reg(self.PWMCONF, pwmconf)

    def release_motor(self):
        """Release motor by setting hold current to zero

        This completely disables current to the motor when idle.
        """
        ihold_irun = self.read_reg(self.IHOLD_IRUN)
        ihold_irun &= ~0x1F
        self.write_reg(self.IHOLD_IRUN, ihold_irun)

    def enable_motor(self, run_current=None):
        """Enable the motor with specified current

        Args:
            run_current: Run current 0-31 (None = use current setting)
        """
        chopconf = self.read_reg(self.CHOPCONF)
        if (chopconf & 0x0F) == 0:
            chopconf = (chopconf & ~0x0F) | 4
            self.write_reg(self.CHOPCONF, chopconf)
        pwmconf = self.read_reg(self.PWMCONF)
        pwmconf &= ~(0x03 << self.PWMCONF_FREEWHEEL)  # Clear freewheel bits
        self.write_reg(self.PWMCONF, pwmconf)
        if run_current is not None:
            ihold_irun = self.read_reg(self.IHOLD_IRUN)
            ihold_irun = (ihold_irun & ~(0x1F << 8)) | ((run_current & 0x1F) << 8)
            self.write_reg(self.IHOLD_IRUN, ihold_irun)

    def disable_motor(self, mode="freewheel"):
        """Disable the motor to prevent heat buildup

        Args:
            mode: How to disable the motor
                "release": Set current to zero but keep driver enabled
                "freewheel": Set to freewheel mode and zero current
                "powerdown": Completely disable driver (TOFF=0)
        """
        if mode == "release":
            ihold_irun = self.read_reg(self.IHOLD_IRUN)
            ihold_irun &= ~0x1F
            self.write_reg(self.IHOLD_IRUN, ihold_irun)

        elif mode == "freewheel":
            ihold_irun = self.read_reg(self.IHOLD_IRUN)
            ihold_irun &= ~0x1F
            self.write_reg(self.IHOLD_IRUN, ihold_irun)
            pwmconf = self.read_reg(self.PWMCONF)
            pwmconf &= ~(0x03 << self.PWMCONF_FREEWHEEL)
            pwmconf |= (1 << self.PWMCONF_FREEWHEEL)
            self.write_reg(self.PWMCONF, pwmconf)

        elif mode == "powerdown":
            chopconf = self.read_reg(self.CHOPCONF)
            chopconf &= ~0x0F
            self.write_reg(self.CHOPCONF, chopconf)
