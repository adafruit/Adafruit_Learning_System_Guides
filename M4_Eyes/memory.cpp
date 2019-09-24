//34567890123456789012345678901234567890123456789012345678901234567890123456

#include <unistd.h> // sbrk() function
#include "globals.h"

// RAM functions -----------------------------------------------------------

uint32_t availableRAM(void) {
  char top;                      // Local variable pushed on stack
  return &top - (char *)sbrk(0); // Top of stack minus end of heap
}

// All the flash stuff has now been merged into Arcada library.
