# input_handler.py
import usb.core
import array
import struct
import time
import gc

class InputHandler:
    """Handles user input through mouse and interactions with UI elements"""

    def __init__(self, screen_width, screen_height, staff_y_start, staff_height):
        self.SCREEN_WIDTH = screen_width
        self.SCREEN_HEIGHT = screen_height
        self.STAFF_Y_START = staff_y_start
        self.STAFF_HEIGHT = staff_height

        # Mouse state
        self.last_left_button_state = 0
        self.last_right_button_state = 0
        self.left_button_pressed = False
        self.right_button_pressed = False
        self.mouse = None
        self.buf = None
        self.in_endpoint = None

        # Mouse position
        self.mouse_x = screen_width // 2
        self.mouse_y = screen_height // 2

    """Find the mouse device and enable report protocol"""
    def find_mouse(self):
        """Find the mouse device with multiple retry attempts"""
        MAX_ATTEMPTS = 5
        RETRY_DELAY = 1  # seconds

        for attempt in range(MAX_ATTEMPTS):
            try:
                print(f"Mouse detection attempt {attempt+1}/{MAX_ATTEMPTS}")

                # Constants for USB control transfers
                DIR_OUT = 0
                DIR_IN = 0x80
                REQTYPE_CLASS = 1 << 5
                REQREC_INTERFACE = 1 << 0
                HID_REQ_SET_PROTOCOL = 0x0B

                # Find all USB devices
                devices_found = False
                for device in usb.core.find(find_all=True):
                    devices_found = True
                    print(f"Found device: {device.idVendor:04x}:{device.idProduct:04x}")

                    try:
                        # Try to get device info
                        try:
                            manufacturer = device.manufacturer
                            product = device.product
                        except:
                            manufacturer = "Unknown"
                            product = "Unknown"

                        # Just use whatever device we find
                        self.mouse = device

                        # Try to detach kernel driver
                        try:
                            if hasattr(device, 'is_kernel_driver_active') and device.is_kernel_driver_active(0):
                                device.detach_kernel_driver(0)
                        except Exception as e:
                            print(f"Error detaching kernel driver: {e}")

                        # Set configuration
                        try:
                            device.set_configuration()
                        except Exception as e:
                            print(f"Error setting configuration: {e}")
                            continue  # Try next device

                        # Just assume endpoint 0x81 (common for mice)
                        self.in_endpoint = 0x81
                        print(f"Using mouse: {manufacturer}, {product}")

                        # Set to report protocol mode
                        try:
                            bmRequestType = (DIR_OUT | REQTYPE_CLASS | REQREC_INTERFACE)
                            bRequest = HID_REQ_SET_PROTOCOL
                            wValue = 1  # 1 = report protocol
                            wIndex = 0  # First interface

                            buf = bytearray(1)
                            device.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, buf)
                            print("Set to report protocol mode")
                        except Exception as e:
                            print(f"Could not set protocol: {e}")

                        # Buffer for reading data
                        self.buf = array.array("B", [0] * 4)
                        print("Created 4-byte buffer for mouse data")

                        # Verify mouse works by reading from it
                        try:
                            # Try to read some data with a short timeout
                            data = device.read(self.in_endpoint, self.buf, timeout=100)
                            print(f"Mouse test read successful: {data} bytes")
                            return True
                        except usb.core.USBTimeoutError:
                            # Timeout is normal if mouse isn't moving
                            print("Mouse connected but not sending data (normal)")
                            return True
                        except Exception as e:
                            print(f"Mouse test read failed: {e}")
                            # Continue to try next device or retry
                            self.mouse = None
                            self.in_endpoint = None
                            continue

                    except Exception as e:
                        print(f"Error initializing device: {e}")
                        continue

                if not devices_found:
                    print("No USB devices found")

                # If we get here without returning, no suitable mouse was found
                print(f"No working mouse found on attempt {attempt+1}, retrying...")
                import gc
                gc.collect()
                import time
                time.sleep(RETRY_DELAY)

            except Exception as e:
                print(f"Error during mouse detection: {e}")
                import gc
                gc.collect()
                import time
                time.sleep(RETRY_DELAY)

        print("Failed to find a working mouse after multiple attempts")
        return False

    def process_mouse_input(self):
        """Process mouse input - simplified version without wheel support"""
        try:
            # Attempt to read data from the mouse (10ms timeout)
            count = self.mouse.read(self.in_endpoint, self.buf, timeout=10)

            if count >= 3:  # We need at least buttons, X and Y
                # Extract mouse button states
                buttons = self.buf[0]
                x = self.buf[1]
                y = self.buf[2]

                # Convert to signed values if needed
                if x > 127:
                    x = x - 256
                if y > 127:
                    y = y - 256

                # Extract button states
                current_left_button_state = buttons & 0x01
                current_right_button_state = (buttons & 0x02) >> 1

                # Detect button presses
                if current_left_button_state == 1 and self.last_left_button_state == 0:
                    self.left_button_pressed = True
                else:
                    self.left_button_pressed = False

                if current_right_button_state == 1 and self.last_right_button_state == 0:
                    self.right_button_pressed = True
                else:
                    self.right_button_pressed = False

                # Update button states
                self.last_left_button_state = current_left_button_state
                self.last_right_button_state = current_right_button_state

                # Update position
                self.mouse_x += x
                self.mouse_y += y

                # Ensure position stays within bounds
                self.mouse_x = max(0, min(self.SCREEN_WIDTH - 1, self.mouse_x))
                self.mouse_y = max(0, min(self.SCREEN_HEIGHT - 1, self.mouse_y))

                return True

            return False

        except usb.core.USBError as e:
            # Handle timeouts silently
            if e.errno == 110:  # Operation timed out
                return False

            # Handle disconnections
            if e.errno == 19:  # No such device
                print("Mouse disconnected")
                self.mouse = None
                self.in_endpoint = None
                import gc
                gc.collect()

            return False
        except Exception as e:
            print(f"Error reading mouse: {type(e).__name__}")
            return False

    def point_in_rect(self, x, y, rect_x, rect_y, rect_width, rect_height):
        """Check if a point is inside a rectangle"""
        return (rect_x <= x < rect_x + rect_width and
                rect_y <= y < rect_y + rect_height)

    def is_over_staff(self, y):
        """Check if mouse is over the staff area"""
        return (self.STAFF_Y_START <= y <= self.STAFF_Y_START + self.STAFF_HEIGHT)
