#include <Arduino.h>

#define DEFAULT_SSID "MY_SSID"
#define DEFAULT_PASSWORD "MY_PASSWORD"
#define DEFAULT_HOSTNAME "esphole"
#define DEFAULT_HOSTFILE "https://gist.githubusercontent.com/ladyada/72a40d8fd39a7d81169ccdf061e7b89a/raw/28815aa1cbb34a9eb373beece504f3843a79cb4f/hosts.txt"

#define TIMEZONE "GMT+0BST-1,M3.5.0/01:00:00,M10.5.0/02:00:00" // local timezone string (https://sites.google.com/a/usapiens.com/opnode/time-zones)


#define EXPOSE_FS_ON_MSD
#define DBG_OUTPUT_PORT Serial

// uncomment to have more output
//#define DEBUG_ESP_DNS


static const size_t MIN_MEMORY = 20000; // minimum amount of memory to keep free
static const size_t MAX_LINELEN = 200; // max length of line processed in downloaded blocklists
static const uint8_t UPDATE_HOUR = 4; // do daily blocklist update at 4am
static const size_t MAX_DOMAINS = 65535; // maximum number of domains, >64K crashes esp32 

static const byte DNS_PORT = 53;

uint32_t flashFreeSpace(void);
