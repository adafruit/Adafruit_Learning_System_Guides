#include "config.h"
#include "SdFat.h"
#include "Adafruit_SPIFlash.h"
#include "Adafruit_TinyUSB.h"
#include <ArduinoJson.h>


#if defined(EXPOSE_FS_ON_MSD)
// USB Mass Storage object
Adafruit_USBD_MSC usb_msc;
#endif


volatile bool fs_changed = false;
extern Adafruit_FlashTransport_ESP32 flashTransport;  // internal SPI flash access
extern Adafruit_SPIFlash flash; 
extern FatFileSystem fatfs;  // file system object from SdFat


const char *secrets_filename = "secrets.json";
StaticJsonDocument<512> doc;
extern char ssid[80];
extern char password[80];
extern char hostname[80];
extern char hostfile[255];

int32_t msc_read_cb (uint32_t lba, void* buffer, uint32_t bufsize);
int32_t msc_write_cb (uint32_t lba, uint8_t* buffer, uint32_t bufsize);
void msc_flush_cb (void);

bool init_filesystem(void) {
  #if defined(EXPOSE_FS_ON_MSD)
  // Set disk vendor id, product id and revision with string up to 8, 16, 4 characters respectively
  usb_msc.setID("Adafruit", "External Flash", "1.0");

  // Set callback
  usb_msc.setReadWriteCallback(msc_read_cb, msc_write_cb, msc_flush_cb);

  // Set disk size, block size should be 512 regardless of spi flash page size
  usb_msc.setCapacity(flash.size()/512, 512);

  // MSC is ready for read/write
  usb_msc.setUnitReady(true);
  
  usb_msc.begin();
#endif

  // Init file system on the flash
  if (! fatfs.begin(&flash)) {
    return false;
  }

  DBG_OUTPUT_PORT.begin(115200);
  DBG_OUTPUT_PORT.setDebugOutput(true);
  DBG_OUTPUT_PORT.println("Adafruit TinyUSB Mass Storage External Flash example");
  DBG_OUTPUT_PORT.print("JEDEC ID: 0x"); 
  DBG_OUTPUT_PORT.println(flash.getJEDECID(), HEX);
  DBG_OUTPUT_PORT.print("Flash size: "); 
  DBG_OUTPUT_PORT.print(flash.size() / 1024); 
  DBG_OUTPUT_PORT.println(" KB");
  DBG_OUTPUT_PORT.print("\n");

  File root = fatfs.open("/");
  File file;
  if (! root)  {
    DBG_OUTPUT_PORT.println("Couldn't open filesystem?");
    return false;
  }
  DBG_OUTPUT_PORT.println("Flash contents:");

  // Open next file in root.
  // Warning, openNext starts at the current directory position
  // so a rewind of the directory may be required.
  while ( file.openNext(&root, O_RDONLY) )
  {
    file.printFileSize(&DBG_OUTPUT_PORT);
    DBG_OUTPUT_PORT.write(' ');
    file.printName(&DBG_OUTPUT_PORT);
    if ( file.isDir() )
    {
      // Indicate a directory.
      DBG_OUTPUT_PORT.write('/');
    }
    DBG_OUTPUT_PORT.println();
    file.close();
  }
  root.close();
  DBG_OUTPUT_PORT.println();

  Serial.printf("Free space: %d bytes\n", flashFreeSpace());
  
  return true;
}


size_t flashFreeSpace(void) {
   size_t freeclust = fatfs.vol()->freeClusterCount();
   return freeclust*512; 
}

bool parseSecrets() {
  // open file for parsing
  File secretsFile = fatfs.open(secrets_filename);
  if (!secretsFile) {
    DBG_OUTPUT_PORT.println("ERROR: Could not open secrets.json file for reading!");
    return false;
  }

  // check if we can deserialize the secrets.json file
  DeserializationError err = deserializeJson(doc, secretsFile);
  if (err) {
    DBG_OUTPUT_PORT.println("ERROR: deserializeJson() failed with code ");
    DBG_OUTPUT_PORT.println(err.c_str());

    return false;
  }

  // next, we detect the network interface from the `secrets.json`
  DBG_OUTPUT_PORT.println("Attempting to find network interface...");
  strlcpy(ssid, doc["ssid"] | DEFAULT_SSID, sizeof(ssid));
  strlcpy(password, doc["password"] | DEFAULT_PASSWORD, sizeof(password));
  strlcpy(hostname, doc["hostname"] | DEFAULT_HOSTNAME, sizeof(hostname));
  strlcpy(hostfile, doc["hostfile"] | DEFAULT_HOSTFILE, sizeof(hostfile));
       
  // close the tempFile
  secretsFile.close();
  return true;
}



// Callback invoked when received READ10 command.
// Copy disk's data to buffer (up to bufsize) and 
// return number of copied bytes (must be multiple of block size) 
int32_t msc_read_cb (uint32_t lba, void* buffer, uint32_t bufsize)
{
  // Note: SPIFLash Block API: readBlocks/writeBlocks/syncBlocks
  // already include 4K sector caching internally. We don't need to cache it, yahhhh!!
  return flash.readBlocks(lba, (uint8_t*) buffer, bufsize/512) ? bufsize : -1;
}

// Callback invoked when received WRITE10 command.
// Process data in buffer to disk's storage and 
// return number of written bytes (must be multiple of block size)
int32_t msc_write_cb (uint32_t lba, uint8_t* buffer, uint32_t bufsize)
{
  digitalWrite(LED_BUILTIN, HIGH);

  // Note: SPIFLash Block API: readBlocks/writeBlocks/syncBlocks
  // already include 4K sector caching internally. We don't need to cache it, yahhhh!!
  return flash.writeBlocks(lba, buffer, bufsize/512) ? bufsize : -1;
}

// Callback invoked when WRITE10 command is completed (status received and accepted by host).
// used to flush any pending cache.
void msc_flush_cb (void)
{
  // sync with flash
  flash.syncBlocks();

  // clear file system's cache to force refresh
  fatfs.cacheClear();

  fs_changed = true;

  digitalWrite(LED_BUILTIN, LOW);
}
