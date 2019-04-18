/* EXAMPLE
$PSRF103,<msg>,<mode>,<rate>,<cksumEnable>*CKSUM<CR><LF>
<msg> 00=GGA,01=GLL,02=GSA,03=GSV,04=RMC,05=VTG
<mode> 00=SetRate,01=Query
<rate> Output every <rate>seconds, off=00,max=255
<cksumEnable> 00=disable Checksum,01=Enable checksum for specified message
Note: checksum is required
Example 1: Query the GGA message with checksum enabled
$PSRF103,00,01,00,01*25
Example 2: Enable VTG message for a 1Hz constant output with checksum enabled
$PSRF103,05,00,01,01*20
Example 3: Disable VTG message
$PSRF103,05,00,00,01*21
*/

#define SERIAL_SET   "$PSRF100,01,4800,08,01,00*0E\r\n"

// GGA-Global Positioning System Fixed Data, message 103,00

#define GGA_ON   "$PSRF103,00,00,01,01*25\r\n"
#define GGA_OFF  "$PSRF103,00,00,00,01*24\r\n"

// GLL-Geographic Position-Latitude/Longitude, message 103,01

#define GLL_ON   "$PSRF103,01,00,01,01*26\r\n"
#define GLL_OFF  "$PSRF103,01,00,00,01*27\r\n"

// GSA-GNSS DOP and Active Satellites, message 103,02

#define GSA_ON   "$PSRF103,02,00,01,01*27\r\n"
#define GSA_OFF  "$PSRF103,02,00,00,01*26\r\n"

// GSV-GNSS Satellites in View, message 103,03

#define GSV_ON   "$PSRF103,03,00,01,01*26\r\n"
#define GSV_OFF  "$PSRF103,03,00,00,01*27\r\n"

// RMC-Recommended Minimum Specific GNSS Data, message 103,04

#define RMC_ON   "$PSRF103,04,00,01,01*21\r\n"
#define RMC_OFF  "$PSRF103,04,00,00,01*20\r\n"

// VTG-Course Over Ground and Ground Speed, message 103,05

#define VTG_ON   "$PSRF103,05,00,01,01*20\r\n"
#define VTG_OFF  "$PSRF103,05,00,00,01*21\r\n"

// Switch Development Data Messages On/Off, message 105
#define LOG_DDM 1
#define DDM_ON   "$PSRF105,01*3E\r\n"
#define DDM_OFF  "$PSRF105,00*3F\r\n"

#define USE_WAAS   0     // useful in US, but slower fix
#define WAAS_ON    "$PSRF151,01*3F\r\n"       // the command for turning on WAAS
#define WAAS_OFF   "$PSRF151,00*3E\r\n"       // the command for turning off WAAS
