//34567890123456789012345678901234567890123456789012345678901234567890123456

#include <unistd.h> // sbrk() function
#include "globals.h"

// RAM functions -----------------------------------------------------------

uint32_t availableRAM(void) {
  char top;                      // Local variable pushed on stack
  return &top - (char *)sbrk(0); // Top of stack minus end of heap
}

// NVM (Non-Volatile Memory, i.e. flash) functions -------------------------

#define FLASH_PAGE_SIZE  (8 << NVMCTRL->PARAM.bit.PSZ)
#define FLASH_NUM_PAGES  NVMCTRL->PARAM.bit.NVMP
#define FLASH_SIZE       (FLASH_PAGE_SIZE * FLASH_NUM_PAGES)
#define FLASH_BLOCK_SIZE (FLASH_PAGE_SIZE * 16) // Datasheet 25.6.2

extern uint32_t __etext; // CODE END. Symbol exported from linker script
static uint8_t *flashAddress = NULL; // Initted on first use below

uint32_t availableNVM(void) {
  if(flashAddress == NULL) {
    // On first call, initialize flashAddress to first block boundary
    // following program storage. Code is uploaded page-at-a-time and
    // any trailing bytes in the last program block may be gibberish,
    // so we can't make use of that for ourselves.
    flashAddress = (uint8_t *)&__etext; // OK to overwrite the '0' there
    if((uint32_t)flashAddress % FLASH_BLOCK_SIZE) {
      flashAddress = &flashAddress[FLASH_BLOCK_SIZE -
        ((uint32_t)flashAddress % FLASH_BLOCK_SIZE)];
    }
  } else {
    // On subsequent calls, round up to next quadword (16 byte) boundary,
    // try packing some data into the trailing bytes of the last-used flash
    // block! Saves up to (8K-16) bytes flash per call.
    if((uint32_t)flashAddress & 15) {
      flashAddress = &flashAddress[16 - ((uint32_t)flashAddress & 15)];
    }
  }
  return FLASH_SIZE - (uint32_t)flashAddress;
}

static inline void wait_ready(void) {
  while(!NVMCTRL->STATUS.bit.READY);
}

// Write a block of data to the NEXT AVAILABLE position in flash memory
// (NOT a specific location). Returns pointer to stored data, NULL if
// insufficient space or error.
uint8_t *writeDataToFlash(uint8_t *ramAddress, uint32_t len) {

  // availableNVM(), aside from reporting the amount of free flash memory,
  // also adjusts flashAddress to the first/next available usable boundary.
  // No need to do that manually here.
  if(len > availableNVM()) {
    Serial.println("Too large!");
    return NULL;
  }

  uint16_t saveCache = NVMCTRL->CTRLA.reg; // Cache in Rev a silicon
  NVMCTRL->CTRLA.bit.CACHEDIS0 = true;     // isn't reliable when
  NVMCTRL->CTRLA.bit.CACHEDIS1 = true;     // writing to NVM.

  // Set manual write mode - only needed once, not in loop
  NVMCTRL->CTRLA.bit.WMODE = NVMCTRL_CTRLA_WMODE_MAN;

  // Clear page buffer, only needed once, quadword write also clears it
  NVMCTRL->CTRLB.reg = NVMCTRL_CTRLB_CMDEX_KEY | NVMCTRL_CTRLB_CMD_PBC;

  for(uint8_t tries = 0;;) { // Repeat write sequence until success or limit

    uint8_t  *src = (uint8_t *)ramAddress;    // Maintain passed-in pointers,
    uint32_t *dst = (uint32_t *)flashAddress; // modify these instead.
    int32_t   bytesThisPass, bytesToGo = len;

    Serial.print("Storing");
    wait_ready(); // Wait for any NVM write op in progress

    while(bytesToGo > 0) {
      // Because dst (via flashAddress) is always quadword-aligned at this
      // point, and flash blocks are known to be a quadword-multiple size,
      // this comparison is reasonable for checking for start of block...
      if(!((uint32_t)dst % FLASH_BLOCK_SIZE)) { // At block boundary
        // If ANY changed data within the entire block, it must be erased
        bytesThisPass = min(FLASH_BLOCK_SIZE, bytesToGo);
        if(memcmp(src, dst, bytesThisPass)) { // >0 if different
          Serial.write('-');                  // minus = erasing
          wait_ready();
          NVMCTRL->ADDR.reg  = (uint32_t)dst; // Destination address in flash
          NVMCTRL->CTRLB.reg = NVMCTRL_CTRLB_CMDEX_KEY | NVMCTRL_CTRLB_CMD_EB;
        } else { // Skip entire block
          Serial.print(">>");                 // >> = skipping, already stored
          bytesToGo -= bytesThisPass;
          src       += FLASH_BLOCK_SIZE;      // Advance to next block
          dst       += FLASH_BLOCK_SIZE / 4;
          continue;
        }
      }

      // Examine next quadword, write only if needed (reduce flash wear)
      bytesThisPass = min(16, bytesToGo);
      if(memcmp(src, dst, bytesThisPass)) { // >0 if different
        if(!((uint32_t)dst & 2047)) Serial.write('.'); // One . per 2KB
        // src might not be 32-bit aligned and must be read byte-at-a-time.
        // dst write ops MUST be 32-bit! Won't work with memcpy().
        dst[0] = src[ 0] | (src[ 1]<<8) | (src[ 2]<<16) | (src[ 3]<<24);
        dst[1] = src[ 4] | (src[ 5]<<8) | (src[ 6]<<16) | (src[ 7]<<24);
        dst[2] = src[ 8] | (src[ 9]<<8) | (src[10]<<16) | (src[11]<<24);
        dst[3] = src[12] | (src[13]<<8) | (src[14]<<16) | (src[15]<<24);
        // Trigger the quadword write
        wait_ready();
        NVMCTRL->ADDR.reg  = (uint32_t)dst;
        NVMCTRL->CTRLB.reg = NVMCTRL_CTRLB_CMDEX_KEY | NVMCTRL_CTRLB_CMD_WQW;
      }
      bytesToGo -= bytesThisPass;
      src       += 16; // Advance to next quadword
      dst       +=  4;
    }

    wait_ready(); // Wait for last write to finish

    Serial.print("verify..."); Serial.flush();
    if(memcmp(ramAddress, flashAddress, len)) { // nonzero if mismatch
      if(++tries >= 4) {
        Serial.println("...proceeding anyway");
        break; // Give up, run with the data we have
      }
      // If we didn't start at a block boundary...
      if(uint32_t q = (uint32_t)flashAddress % FLASH_BLOCK_SIZE) {
        // Get index of first changed byte
        uint32_t n;
        for(n=0; (ramAddress[n] == flashAddress[n]) &&
          (n <= FLASH_BLOCK_SIZE); n++);
        // ...and if first mismatched byte is within the region before
        // the first block boundary...
        q = FLASH_BLOCK_SIZE - q; // Bytes in partial 1st block
        if(n < q) {
          // ...then flashAddress MUST be advanced to the next block
          // boundary before we retry, reason being that we CAN'T erase
          // the initial partial block (it may be preceded by other data).
          flashAddress = &flashAddress[q];
        }
      }
      Serial.println("...retrying..."); Serial.flush();
    } else {
      Serial.println("OK");
      break;
    }
  }

  NVMCTRL->CTRLA.reg = saveCache; // Restore NVM cache settings

  // Return value will be start of newly-written data in flash
  uint8_t *returnVal = flashAddress;
  // Move next flash address past new data
  // No need to align to next boundary, done at top of next call
  flashAddress += len;
  return returnVal;
}
