add_executable(serial_passthrough
  serial_passthrough.c
        )

# Pull in our pico_stdlib which pulls in commonly used features
target_link_libraries(serial_passthrough pico_stdlib)

# create map/bin/hex file etc.
pico_add_extra_outputs(serial_passthrough)

# add url via pico_set_program_url
example_auto_set_url(serial_passthrough)

# enable usb output, disable uart output
pico_enable_stdio_usb(serial_passthrough 1)
pico_enable_stdio_uart(serial_passthrough 0)