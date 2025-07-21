# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Thermal Camera Overlay for Raspberry Pi 4,
PiCamera 3 and STEMMA MLX90640

Inspired by PitFusion Thermal Imager
"""

import time
import numpy as np
import cv2
import board
import busio
import adafruit_mlx90640
from picamera2 import Picamera2
from PIL import Image

# Temperature range for thermal camera (in Celsius)
MIN_TEMP = 20.0
MAX_TEMP = 35.0

# Thermal overlay opacity (0.0 = invisible, 1.0 = fully opaque)
THERMAL_OPACITY = 0.7

# Display window size
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Camera settings
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

SKIP_FRAMES = 2  # Process every Nth frame for thermal
frame_counter = 0

# Thermal camera size
THERMAL_WIDTH = 32
THERMAL_HEIGHT = 24

# Thermal zoom factor (1.7x to compensate for FoV difference)
# Thermal camera FoV: 110°x75°, Pi camera FoV: 66°x41°
# Ratio: 66/110 = 0.6, so we need 1/0.6 = 1.67x zoom
THERMAL_ZOOM = 1.7

# Camera crop settings to compensate for thermal offset
# This crops the camera image to match the thermal coverage area
CAMERA_CROP_LEFT = 65    # Match thermal X offset
CAMERA_CROP_TOP = 85     # Match thermal Y offset
CAMERA_CROP_RIGHT = 0    # No crop on right
CAMERA_CROP_BOTTOM = 0   # No crop on bottom

# Calculate effective camera size after cropping
CAMERA_CROP_WIDTH = CAMERA_WIDTH - CAMERA_CROP_LEFT - CAMERA_CROP_RIGHT
CAMERA_CROP_HEIGHT = CAMERA_HEIGHT - CAMERA_CROP_TOP - CAMERA_CROP_BOTTOM

# ============= SETUP THERMAL CAMERA =============
print("Setting up thermal camera...")
i2c = busio.I2C(board.SCL, board.SDA)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ

# Create array to hold thermal data
thermal_frame = np.zeros(768, dtype=np.float32)

# ============= SETUP REGULAR CAMERA =============
print("Setting up Pi camera...")
picam2 = Picamera2()
camera_config = picam2.create_preview_configuration(
    main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "RGB888"},
    buffer_count=2,  # Reduce buffer count for lower latency
    queue=False  # Don't queue frames
)
picam2.configure(camera_config)
picam2.start()
picam2.set_controls({"ExposureTime": 20000, "AnalogueGain": 1.0})
time.sleep(2)

# ============= CREATE THERMAL COLORMAP =============
def create_thermal_colormap():
    """Create a colormap for thermal visualization"""
    # Define color points (blue -> cyan -> green -> yellow -> orange -> red)
    colors = np.array([
        [0, 0, 64],       # Dark blue (cold)
        [0, 0, 255],      # Blue
        [0, 255, 255],    # Cyan
        [0, 255, 0],      # Green
        [255, 255, 0],    # Yellow
        [255, 128, 0],    # Orange
        [255, 0, 0],      # Red (hot)
    ], dtype=np.uint8)

    # Create smooth gradient between colors
    colormap = np.zeros((256, 3), dtype=np.uint8)
    positions = np.linspace(0, len(colors)-1, 256)

    for i in range(256):
        pos = positions[i]
        idx = int(pos)
        frac = pos - idx

        if idx >= len(colors) - 1:
            colormap[i] = colors[-1]
        else:
            colormap[i] = (1 - frac) * colors[idx] + frac * colors[idx + 1]

    colormap = colormap[::-1]  # Reverse the colormap
    return colormap
the_colormap = create_thermal_colormap()

# ============= HELPER FUNCTIONS =============
def process_thermal_frame(thermal_data, colormap):
    """Convert thermal data to colored image"""
    # Calculate temperature statistics
    min_temp = np.min(thermal_data)
    max_temp = np.max(thermal_data)
    avg_temp = np.mean(thermal_data)
    if min_temp < -100:
        min_temp = MIN_TEMP
        avg_temp = (MIN_TEMP + MAX_TEMP) / 2

    # Normalize temperature data to 0-255 range
    normalized = np.clip(
        (thermal_data - MIN_TEMP) / (MAX_TEMP - MIN_TEMP) * 255,
        0, 255
    ).astype(np.uint8)

    # Apply colormap
    colored = colormap[normalized]

    # Reshape to 2D image (24x32x3)
    thermal_image = colored.reshape(THERMAL_HEIGHT, THERMAL_WIDTH, 3)

    # Flip horizontally to match camera view
    thermal_image = np.fliplr(thermal_image)

    # Scale up to camera size using PIL for smooth interpolation
    pil_thermal = Image.fromarray(thermal_image)

    # Apply zoom by scaling to a larger size than the camera
    scaled_width = int(CAMERA_WIDTH * THERMAL_ZOOM)
    scaled_height = int(CAMERA_HEIGHT * THERMAL_ZOOM)
    pil_thermal = pil_thermal.resize((scaled_width, scaled_height), Image.BICUBIC)

    # Crop the center to match camera size (this creates the zoom effect)
    thermal_array = np.array(pil_thermal)
    crop_x = (scaled_width - CAMERA_WIDTH) // 2
    crop_y = (scaled_height - CAMERA_HEIGHT) // 2
    thermal_cropped = thermal_array[crop_y:crop_y+CAMERA_HEIGHT, crop_x:crop_x+CAMERA_WIDTH]

    return thermal_cropped, min_temp, max_temp, avg_temp

def blend_images(camera_image, thermal_image, opacity):
    """Blend camera and thermal images with position offset"""
    # Create a canvas the same size as the camera image
    canvas = camera_image.copy()

    # Calculate position with offset
    x_offset = 0
    y_offset = 0

    # Ensure the thermal image fits within bounds
    x_start = max(0, x_offset)
    y_start = max(0, y_offset)
    x_end = min(camera_image.shape[1], x_offset + thermal_image.shape[1])
    y_end = min(camera_image.shape[0], y_offset + thermal_image.shape[0])

    # Calculate the corresponding region in the thermal image
    thermal_x_start = max(0, -x_offset)
    thermal_y_start = max(0, -y_offset)
    thermal_x_end = thermal_x_start + (x_end - x_start)
    thermal_y_end = thermal_y_start + (y_end - y_start)

    # Blend only the overlapping region
    if x_end > x_start and y_end > y_start:
        canvas[y_start:y_end, x_start:x_end] = (
            canvas[y_start:y_end, x_start:x_end] * (1 - opacity) +
            thermal_image[thermal_y_start:thermal_y_end, thermal_x_start:thermal_x_end] * opacity
        )

    return canvas.astype(np.uint8)

def add_temperature_scale(image, colormap):
    """Add temperature scale bar to the image"""
    # Create scale bar
    scale_height = 20
    scale_width = 200
    scale_x = image.shape[1] - scale_width - 20
    scale_y = 90  # Moved down to make room for buttons

    # Draw temperature gradient
    for i in range(scale_width):
        temp_normalized = i / scale_width
        color_idx = int(temp_normalized * 255)
        color = colormap[color_idx]
        cv2.line(image,
                 (scale_x + i, scale_y),
                 (scale_x + i, scale_y + scale_height),
                 color.tolist(), 1)

    # Add temperature labels
    cv2.putText(image, f"{MIN_TEMP:.0f}C",
                (scale_x - 35, scale_y + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(image, f"{MAX_TEMP:.0f}C",
                (scale_x + scale_width + 5, scale_y + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Draw border around scale
    cv2.rectangle(image,
                  (scale_x - 1, scale_y - 1),
                  (scale_x + scale_width + 1, scale_y + scale_height + 1),
                  (255, 255, 255), 1)

# ============= MAIN LOOP =============
print("Starting thermal camera overlay...")
print("Use Up/Down keys to increase/decrease max temp")
print("Use Left/Right keys to increase/decrease min temp")
print("Use +/- keys to increase/decrease overlay opacity")
print("Use Q key to exit")

cv2.namedWindow('Thermal Overlay', cv2.WINDOW_NORMAL)
cv2.resizeWindow('Thermal Overlay', WINDOW_WIDTH, WINDOW_HEIGHT)

# Temperature statistics
temp_stats = {"min": 0, "max": 0, "avg": 0}
last_thermal_colored = None

try:
    while True:

        # Read thermal data (only every SKIP_FRAMES frames)
        if frame_counter % SKIP_FRAMES == 0:
            try:
                mlx.getFrame(thermal_frame)
                # Process thermal data to colored image
                last_thermal_colored, temp_stats["min"], temp_stats["max"], temp_stats["avg"] = process_thermal_frame(thermal_frame, the_colormap) # pylint: disable=line-too-long
            except Exception as e: # pylint: disable=broad-except
                print(f"Thermal read error: {e}")

        frame_counter += 1

        # Use the last processed thermal frame
        if last_thermal_colored is not None:
            thermal_colored = last_thermal_colored
        else:
            # Create a blank thermal image if we don't have one yet
            thermal_colored = np.zeros((CAMERA_HEIGHT, CAMERA_WIDTH, 3), dtype=np.uint8)

        # Capture camera frame
        camera_frame = picam2.capture_array()

        # Crop the camera frame to match thermal coverage area
        camera_cropped = camera_frame[
            CAMERA_CROP_TOP:CAMERA_HEIGHT-CAMERA_CROP_BOTTOM,
            CAMERA_CROP_LEFT:CAMERA_WIDTH-CAMERA_CROP_RIGHT
        ]

        # Resize cropped camera back to full display size
        camera_resized = cv2.resize(camera_cropped, (CAMERA_WIDTH, CAMERA_HEIGHT),
                                                   interpolation=cv2.INTER_LINEAR)

        # Blend camera and thermal images (now both are aligned)
        overlay_image = blend_images(camera_resized, thermal_colored, THERMAL_OPACITY)

        # Add temperature scale
        add_temperature_scale(overlay_image, the_colormap)

        # Add status text with temperature statistics and FPS
        status_text = f"Range: {MIN_TEMP:.0f}-{MAX_TEMP:.0f}C | Opacity: {THERMAL_OPACITY:.1f} | "
        status_text += f"Min: {temp_stats['min']:.1f}C | Max: {temp_stats['max']:.1f}C | Avg: {temp_stats['avg']:.1f}C | "  # pylint: disable=line-too-long
        cv2.putText(overlay_image, status_text,
                    (10, overlay_image.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Display the image
        cv2.imshow('Thermal Overlay', overlay_image)

        # Check if window was closed
        if cv2.getWindowProperty('Thermal Overlay', cv2.WND_PROP_VISIBLE) < 1:
            break

        key_action = cv2.waitKey(1) & 0xFF
        if key_action == ord('q'):
            raise KeyboardInterrupt
        if key_action == 82:
            MAX_TEMP = min(MAX_TEMP + 1, 100)
            print(f"Max temp: {MAX_TEMP:.1f}C")
        elif key_action == 84:
            MAX_TEMP = max(MAX_TEMP - 1, MIN_TEMP + 1)
            print(f"Max temp: {MAX_TEMP:.1f}C")
        elif key_action == 81:
            MIN_TEMP = max(MIN_TEMP - 1, -20)
            print(f"Min temp: {MIN_TEMP:.1f}C")
        elif key_action == 83:
            MIN_TEMP = min(MIN_TEMP + 1, MAX_TEMP - 1)
            print(f"Min temp: {MIN_TEMP:.1f}C")
        elif key_action == ord('+'):
            THERMAL_OPACITY = min(THERMAL_OPACITY + 0.1, 1.0)
            print(f"Opacity: {THERMAL_OPACITY:.1f}")
        elif key_action == ord('-'):
            THERMAL_OPACITY = max(THERMAL_OPACITY - 0.1, 0.0)
            print(f"Opacity: {THERMAL_OPACITY:.1f}")
        elif key_action == ord('z'):
            THERMAL_OPACITY = not THERMAL_OPACITY
            print(f"Opacity: {THERMAL_OPACITY:.1f}")

except KeyboardInterrupt:
    print("\nShutting down...")

finally:
    print("Cleaning up...")
    cv2.destroyAllWindows()
    cv2.waitKey(1)
    picam2.stop()
