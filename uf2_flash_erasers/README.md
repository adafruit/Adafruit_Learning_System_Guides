These UF2 files load all zeros into all of flash, skipping the bootloader section.

* `erase_m0.uf2` writes 256k-8k of zeros starting at 8k
* `erase_m4.uf2` writes 512k-16k of zeros starting at 16k

These are useful for clearing out damaged CIRCUITPY filesystems in internal flash.

Example of how to create erase-m4.uf2, which assume 512k of flash and a 16k bootloader:
```sh
$ truncate -s 507904 512k-16k.bin   # 507904 is 512k minus 16k
$ circuitpython/tools/uf2/utils/uf2conv.py -c -b 16384 512k-16k.bin -o 512k-16k.uf2
$ mv 512k-16k.uf2 erase-m4.uf2
```

These don't erase CIRCUITPY in SPI flash, such as on Express boards. For flash erasers for SPI flash, see https://github.com/adafruit/Adafruit_SPIFlash/tree/master/examples/flash_erase_express.
