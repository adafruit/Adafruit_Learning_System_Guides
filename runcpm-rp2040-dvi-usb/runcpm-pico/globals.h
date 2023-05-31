// SPDX-FileCopyrightText: 2023 Mockba the Borg
//
// SPDX-License-Identifier: MIT

#ifndef GLOBALS_H
#define GLOBALS_H

/* Some definitions needed globally */
#ifdef __MINGW32__
#include <ctype.h>
#endif

/* Definition for enabling incrementing the R register for each M1 cycle */
#define DO_INCR

/* Definitions for enabling PUN: and LST: devices */
#define USE_PUN	// The pun.txt and lst.txt files will appear on drive A: user 0
#define USE_LST

/* Definitions for file/console based debugging */
//#define DEBUG				// Enables the internal debugger (enabled by default on vstudio debug builds)
//#define iDEBUG			// Enables instruction logging onto iDebug.log (for development debug only)
//#define DEBUGLOG			// Writes extensive call trace information to RunCPM.log
//#define CONSOLELOG		// Writes debug information to console instead of file
//#define LOGBIOS_NOT 01	// If defined will not log this BIOS function number
//#define LOGBIOS_ONLY 02	// If defines will log only this BIOS function number
//#define LOGBDOS_NOT 06	// If defined will not log this BDOS function number
//#define LOGBDOS_ONLY 22	// If defines will log only this BDOS function number
#define LogName "RunCPM.log"

/* RunCPM version for the greeting header */
#define VERSION	"6.0"
#define VersionBCD 0x60

/* Definition of which CCP to use (must define only one) */
#define CCP_INTERNAL		// If this is defined, an internal CCP will emulated
//#define CCP_DR
//#define CCP_CCPZ
//#define CCP_ZCPR2
//#define CCP_ZCPR3
//#define CCP_Z80

/* Definition of the CCP memory information */
//
#ifdef CCP_INTERNAL
#define CCPname		"INTERNAL v3.0"			// Will use the CCP from ccp.h
#define VersionCCP	0x30					// 0x10 and above reserved for Internal CCP
#define BatchFCB	(tmpFCB + 48)
#define CCPaddr		BDOSjmppage				// Internal CCP has size 0
#endif
//
#ifdef CCP_DR
#define CCPname		"CCP-DR." STR(TPASIZE) "K"
#define VersionCCP	0x00					// Version to be used by INFO.COM
#define BatchFCB	(CCPaddr + 0x7AC)		// Position of the $$$.SUB fcb on this CCP
#define CCPaddr		(BDOSjmppage-0x0800)	// CCP memory address
#endif
//
#ifdef CCP_CCPZ
#define CCPname		"CCP-CCPZ." STR(TPASIZE) "K"
#define VersionCCP	0x01
#define BatchFCB	(CCPaddr + 0x7A)		// Position of the $$$.SUB fcb on this CCP
#define CCPaddr		(BDOSjmppage-0x0800)
#endif
//
#ifdef CCP_ZCPR2
#define CCPname		"CCP-ZCP2." STR(TPASIZE) "K"
#define VersionCCP	0x02
#define BatchFCB	(CCPaddr + 0x5E)		// Position of the $$$.SUB fcb on this CCP
#define CCPaddr		(BDOSjmppage-0x0800)
#endif
//
#ifdef CCP_ZCPR3
#define CCPname		"CCP-ZCP3." STR(TPASIZE) "K"
#define VersionCCP	0x03
#define BatchFCB	(CCPaddr + 0x5E)		// Position of the $$$.SUB fcb on this CCP
#define CCPaddr		(BDOSjmppage-0x1000)
#endif
//
#ifdef CCP_Z80
#define CCPname		"CCP-Z80." STR(TPASIZE) "K"
#define VersionCCP	0x04
#define BatchFCB	(CCPaddr + 0x79E)		// Position of the $$$.SUB fcb on this CCP
#define CCPaddr		(BDOSjmppage-0x0800)
#endif
//
#ifndef CCPname
#error No CCP defined
#endif
//
#define STR_HELPER(x) #x
#define STR(x) STR_HELPER(x)
// #define CCPHEAD		"\r\nRunCPM Version " VERSION " (CP/M " STR(TPASIZE) "K)\r\n"
#define CCPHEAD    "\r\nRunCPM [\e[1mv" VERSION "\e[0m] => CCP:[\e[1m" CCPname "\e[0m] TPA:[\e[1m" STR(TPASIZE) "K\e[0m]\r\n"

#define NOSLASH						// Will translate '/' to '_' on filenames to prevent directory errors

//#define HASLUA					// Will enable Lua scripting (BDOS call 254)
									// Should be passed externally per-platform with -DHASLUA

//#define PROFILE					// For measuring time taken to run a CP/M command
									// This should be enabled only for debugging purposes when trying to improve emulation speed

#define NOHIGHUSER					// Prevents the creation of user folders above 'F' (15) by programs
									// Original CP/M BDOS allows it, but I prefer to keep the folders clean

/* Definition for CP/M 2.2 user number support */

#define BATCHA						// If this is defined, the $$$.SUB will be looked for on drive A:
//#define BATCH0					// If this is defined, the $$$.SUB will be looked for on user area 0
									// The default behavior of DRI's CP/M 2.2 was to have $$$.SUB created on the current drive/user while looking for it
									// on drive A: current user, which made it complicated to run SUBMITs when not logged to drive A: user 0

/* Some environment and type definitions */

#ifndef TRUE
#define FALSE 0
#define TRUE 1
#endif

typedef signed char     int8;
typedef signed short    int16;
typedef signed int      int32;
typedef unsigned char   uint8;
typedef unsigned short  uint16;
typedef unsigned int    uint32;

#define LOW_DIGIT(x)     ((x) & 0xf)
#define HIGH_DIGIT(x)    (((x) >> 4) & 0xf)
#define LOW_REGISTER(x)  ((x) & 0xff)
#define HIGH_REGISTER(x) (((x) >> 8) & 0xff)

#define SET_LOW_REGISTER(x, v)  x = (((x) & 0xff00) | ((v) & 0xff))
#define SET_HIGH_REGISTER(x, v) x = (((x) & 0xff) | (((v) & 0xff) << 8))

#define WORD16(x)	((x) & 0xffff)

/* CP/M Page 0 definitions */
#define IOByte 0x03
#define DSKByte 0x04

/* CP/M disk definitions */
#define BlkSZ 128					// CP/M block size
#define BlkEX 128					// Number of blocks on an extension
#define ExtSZ (BlkSZ * BlkEX)
#define BlkS2 4096					// Number of blocks on a S2 (module)
#define MaxEX 31					// Maximum value the EX field can take
#define MaxS2 15					// Maximum value the S2 (modules) field can take - Can be set to 63 to emulate CP/M Plus
#define MaxCR 128					// Maximum value the CR field can take
#define MaxRC 128					// Maximum value the RC field can take

/* CP/M memory definitions */
#define TPASIZE 64					// Can be 60 for CP/M 2.2 compatibility or more, up to 64 for extra memory
								          	// Values other than 60 or 64 would require rebuilding the CCP
									          // For TPASIZE<60 CCP ORG = (SIZEK * 1024) - 0x0C00

#define BANKS 1						// Number of memory banks available
static uint8 curBank = 1;			// Number of the current RAM bank in use (1-x, not 0-x)
static uint8 isXmove = FALSE;		// Used by BIOS
static uint8 srcBank = 1;			// Source bank for memory MOVE
static uint8 dstBank = 1;			// Destination bank for memory MOVE
static uint8 ioBank = 1;			// Destination bank for sector IO

#define PAGESIZE 64 * 1024			// RAM(plus ROM) needs to be 64K to avoid compatibility issues
#define MEMSIZE PAGESIZE * BANKS	// Total RAM size

#if BANKS==1
#define RAM_FAST					// If this is defined, all RAM function calls become direct access (see below)
									// This saves about 2K on the Arduino code and should bring speed improvements
#endif

#ifdef RAM_FAST						// Makes all function calls to memory access into direct RAM access (less calls / less code)
	static uint8 RAM[MEMSIZE];
	#define _RamSysAddr(a)		&RAM[a]
	#define _RamRead(a)			RAM[a]
	#define _RamRead16(a)		((RAM[((a) & 0xffff) + 1] << 8) | RAM[(a) & 0xffff])
	#define _RamWrite(a, v)		RAM[a] = v
	#define _RamWrite16(a, v)	RAM[a] = (v) & 0xff; RAM[(a) + 1] = (v) >> 8
#endif

// Size of the allocated pages (Minimum size = 1 page = 256 bytes)

// BIOS Pages (512 bytes from the top of memory)
#define BIOSjmppage	(PAGESIZE - 512)
#define BIOSpage	(BIOSjmppage + 256)

// BDOS Pages (depends on TPASIZE for external CCPs)
#if defined CCP_INTERNAL
	#define BDOSjmppage (BIOSjmppage - 256)
	#define BDOSpage (BDOSjmppage + 16)
#else
	#define BDOSjmppage (TPASIZE * 1024) - 1024
	#define BDOSpage	(BDOSjmppage + 256)
#endif

#define DPBaddr (BIOSpage + 128)	// Address of the Disk Parameter Block (Hardcoded in BIOS)
#define DPHaddr (DPBaddr + 15)		// Address of the Disk Parameter Header 

#define SCBaddr (BDOSpage + 3)		// Address of the System Control Block
#define tmpFCB  (BDOSpage + 16)		// Address of the temporary FCB

/* Definition of global variables */
static uint8	filename[17];		// Current filename in host filesystem format
static uint8	newname[17];		// New filename in host filesystem format
static uint8	fcbname[13];		// Current filename in CP/M format
static uint8	pattern[13];		// File matching pattern in CP/M format
static uint16	dmaAddr = 0x0080;	// Current dmaAddr
static uint8	oDrive = 0;			// Old selected drive
static uint8	cDrive = 0;			// Currently selected drive
static uint8	userCode = 0;		// Current user code
static uint16	roVector = 0;
static uint16	loginVector = 0;
static uint8	allUsers = FALSE;	// true when dr is '?' in BDOS search first
static uint8	allExtents = FALSE;	// true when ex is '?' in BDOS search first
static uint8	currFindUser = 0;	// user number of current directory in BDOS search first on all user numbers
static uint8	blockShift;			// disk allocation block shift
static uint8	blockMask;			// disk allocation block mask
static uint8	extentMask;			// disk extent mask
static uint16	firstBlockAfterDir;	// first allocation block after directory
static uint16	numAllocBlocks;		// # of allocation blocks on disk
static uint8	extentsPerDirEntry;	// # of logical (16K) extents in a directory entry
#define logicalExtentBytes (16*1024UL)
static uint16	physicalExtentBytes;// # bytes described by 1 directory entry

#define tohex(x)	((x) < 10 ? (x) + 48 : (x) + 87)

/* Definition of externs to prevent precedence compilation errors */
#ifdef __cplusplus // If building on Arduino
extern "C"
{
#endif

#ifndef RAM_FAST
	extern uint8* _RamSysAddr(uint16 address);
	extern void _RamWrite(uint16 address, uint8 value);
#endif

	extern void _Bdos(void);
	extern void _Bios(void);

	extern void _HostnameToFCB(uint16 fcbaddr, uint8* filename);
	extern void _HostnameToFCBname(uint8* from, uint8* to);
	extern void _mockupDirEntry(void);
	extern uint8 match(uint8* fcbname, uint8* pattern);

	extern void _puts(const char* str);

#ifdef __cplusplus // If building on Arduino
}
#endif

#endif
