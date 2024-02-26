Import("env", "projenv")

def post_program_action(source, target, env):
    program_path = target[0].get_abspath()
    print("Program has been built at: ", program_path)
    # Use esptool to merge binaries for ESP32-S3
    env.Execute("esptool.py --chip esp32s3 merge_bin -o $BUILD_DIR/merged-firmware.bin --flash_mode dio --flash_freq 80m --flash_size 4MB 0x0000 $BUILD_DIR/bootloader.bin 0x8000 $BUILD_DIR/partitions.bin 0xe000 /Users/brentrubell/.platformio/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin 0x2d0000 /Users/brentrubell/.platformio/packages/framework-arduinoespressif32/variants/adafruit_camera_esp32s3/tinyuf2.bin 0x10000 $BUILD_DIR/firmware.bin")
env.AddPostAction("buildprog", post_program_action)
