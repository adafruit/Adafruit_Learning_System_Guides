// SPDX-FileCopyrightText: 2023 Mockba the Borg
//
// SPDX-License-Identifier: MIT

#ifndef CPM_H
#define CPM_H

enum eBIOSFunc {
// CP/M 2.2 Stuff
	B_BOOT = 0,
	B_WBOOT = 3,
	B_CONST = 6,
	B_CONIN = 9,
	B_CONOUT = 12,
	B_LIST = 15,
	B_AUXOUT = 18,
	B_READER = 21,
	B_HOME = 24,
	B_SELDSK = 27,
	B_SETTRK = 30,
	B_SETSEC = 33,
	B_SETDMA = 36,
	B_READ = 39,
	B_WRITE = 42,
	B_LISTST = 45,
	B_SECTRAN = 48,
// CP/M 3.0 Stuff
	B_CONOST = 51,
	B_AUXIST = 54,
	B_AUXOST = 57,
	B_DEVTBL = 60,
	B_DEVINI = 63,
	B_DRVTBL = 66,
	B_MULTIO = 69,
	B_FLUSH = 72,
	B_MOVE = 75,
	B_TIME = 78,
	B_SELMEM = 81,
	B_SETBNK = 84,
	B_XMOVE = 87,
	B_USERF = 90,	// Used by internal CCP to return to prompt
	B_RESERV1 = 93,
	B_RESERV2 = 96
};

enum eBDOSFunc {
// CP/M 2.2 Stuff
	P_TERMCPM = 0,
	C_READ = 1,
	C_WRITE = 2,
	A_READ = 3,
	A_WRITE = 4,
	L_WRITE = 5,
	C_RAWIO = 6,
	A_STATIN = 7,
	A_STATOUT = 8,
	C_WRITESTR = 9,
	C_READSTR = 10,
	C_STAT = 11,
	S_BDOSVER = 12,
	DRV_ALLRESET = 13,
	DRV_SET = 14,
	F_OPEN = 15,
	F_CLOSE = 16,
	F_SFIRST = 17,
	F_SNEXT = 18,
	F_DELETE = 19,
	F_READ = 20,
	F_WRITE = 21,
	F_MAKE = 22,
	F_RENAME = 23,
	DRV_LOGINVEC = 24,
	DRV_GET = 25,
	F_DMAOFF = 26,
	DRV_ALLOCVEC = 27,
	DRV_SETRO = 28,
	DRV_ROVEC = 29,
	F_ATTRIB = 30,
	DRV_PDB = 31,
	F_USERNUM = 32,
	F_READRAND = 33,
	F_WRITERAND = 34,
	F_SIZE = 35,
	F_RANDREC = 36,
	DRV_RESET = 37,
	DRV_ACCESS = 38,	// This is an MP/M function that is not supported under CP/M 3.
	DRV_FREE = 39,		// This is an MP/M function that is not supported under CP/M 3.
	F_WRITEZF = 40,
// CP/M 3.0 Stuff
	F_TESTWRITE = 41,
	F_LOCKFILE = 42,
	F_UNLOCKFILE = 43,
	F_MULTISEC = 44,
	F_ERRMODE = 45,
	DRV_SPACE = 46,
	P_CHAIN = 47,
	DRV_FLUSH = 48,
	S_SCB = 49,
	S_BIOS = 50,
	P_LOAD = 59,
	S_RSX = 60,
	F_CLEANUP = 98,
	F_TRUNCATE = 99,
	DRV_SETLABEL = 100,
	DRV_GETLABEL = 101,
	F_TIMEDATE = 102,
	F_WRITEXFCB = 103,
	T_SET = 104,
	T_GET = 105,
	F_PASSWD = 106,
	S_SERIAL = 107,
	P_CODE = 108,
	C_MODE = 109,
	C_DELIMIT = 110,
	C_WRITEBLK = 111,
	L_WRITEBLK = 112,
	F_PARSE = 152,
// RunCPM Stuff
	F_RUNLUA = 254
};

/* see main.c for definition */

#define JP 0xc3
#define CALL 0xcd
#define RET 0xc9
#define INa 0xdb    // Triggers a BIOS call
#define OUTa 0xd3   // Triggers a BDOS call

/* set up full PUN and LST filenames to be on drive A: user 0 */
#ifdef USE_PUN
char pun_file[17] = {'A', FOLDERCHAR, '0', FOLDERCHAR, 'P', 'U', 'N', '.', 'T', 'X', 'T', 0};

#endif // ifdef USE_PUN
#ifdef USE_LST
char lst_file[17] = {'A', FOLDERCHAR, '0', FOLDERCHAR, 'L', 'S', 'T', '.', 'T', 'X', 'T', 0};

#endif // ifdef USE_LST

#ifdef PROFILE
unsigned long time_start = 0;
unsigned long time_now = 0;

#endif // ifdef PROFILE

void _PatchCPM(void) {
	uint16 i;

	// **********  Patch CP/M page zero into the memory  **********

	/* BIOS entry point */
	_RamWrite(0x0000,   JP);  /* JP BIOS+3 (warm boot) */
	_RamWrite16(0x0001, BIOSjmppage + 3);
	if (Status != 2) {
		/* IOBYTE - Points to Console */
		_RamWrite(	IOByte,		0x3D);

		/* Current drive/user - A:/0 */
		_RamWrite(	DSKByte,	0x00);
	}
	/* BDOS entry point (0x0005) */
	_RamWrite(0x0005,   JP);
	_RamWrite16(0x0006,	BDOSjmppage + 0x06);

	// **********  Patch CP/M Version into the memory so the CCP can see it
	_RamWrite16(BDOSjmppage,		0x1600);
	_RamWrite16(BDOSjmppage + 2,	0x0000);
	_RamWrite16(BDOSjmppage + 4,	0x0000);

	// Patches in the BDOS jump destination
	_RamWrite(  BDOSjmppage + 6, JP);
	_RamWrite16(BDOSjmppage + 7, BDOSpage);

	// Patches in the BDOS page content
	_RamWrite(	BDOSpage,		INa);
	_RamWrite(	BDOSpage + 1,	0xFF);
	_RamWrite(	BDOSpage + 2,	RET);

	// Patches in the BIOS jump destinations
	for (i = 0; i < 99; i = i + 3) {
		_RamWrite(  BIOSjmppage + i,	 JP);
		_RamWrite16(BIOSjmppage + i + 1, BIOSpage + i);
	}

	// Patches in the BIOS page content
	for (i = 0; i < 99; i = i + 3) {
		_RamWrite(	BIOSpage + i,		OUTa);
		_RamWrite(	BIOSpage + i + 1,	0xFF);
		_RamWrite(	BIOSpage + i + 2,	RET);
	}
	// **********  Patch CP/M (fake) Disk Paramater Block after the BDOS call entry  **********
	i = DPBaddr;
	_RamWrite(	i++,	64);    // spt - Sectors Per Track
	_RamWrite(	i++,	0);
	_RamWrite(	i++,	5);     // bsh - Data allocation "Block Shift Factor"
	_RamWrite(	i++,	0x1F);  // blm - Data allocation Block Mask
	_RamWrite(	i++,	1);     // exm - Extent Mask
	_RamWrite(	i++,	0xFF);  // dsm - Total storage capacity of the disk drive
	_RamWrite(	i++,	0x07);
	_RamWrite(	i++,	255);   // drm - Number of the last directory entry
	_RamWrite(	i++,	3);
	_RamWrite(	i++,	0xFF);  // al0
	_RamWrite(	i++,	0x00);  // al1
	_RamWrite(	i++,	0);     // cks - Check area Size
	_RamWrite(	i++,	0);
	_RamWrite(	i++,	0x02);  // off - Number of system reserved tracks at the beginning of the ( logical ) disk
	_RamWrite(	i++,	0x00);
	blockShift = _RamRead(DPBaddr + 2);
	blockMask = _RamRead(DPBaddr + 3);
	extentMask = _RamRead(DPBaddr + 4);
	numAllocBlocks = _RamRead16(DPBaddr + 5) + 1;
	extentsPerDirEntry = extentMask + 1;

	// **********  Patch CP/M (fake) Disk Parameter Header after the Disk Parameter Block  **********
	_RamWrite(	i++,	0); // Addr of the sector translation table
	_RamWrite(	i++,	0);
	_RamWrite(	i++,	0); // Workspace
	_RamWrite(	i++,	0);
	_RamWrite(	i++,	0);
	_RamWrite(	i++,	0);
	_RamWrite(	i++,	0);
	_RamWrite(	i++,	0);
	_RamWrite(	i++,	0x80);                  // Addr of the Sector Buffer
	_RamWrite(	i++,	0);
	_RamWrite(	i++,	LOW_REGISTER(DPBaddr)); // Addr of the DPB Disk Parameter Block
	_RamWrite(	i++,	HIGH_REGISTER(DPBaddr));
	_RamWrite(	i++,	0);                     // Addr of the Directory Checksum Vector
	_RamWrite(	i++,	0);
	_RamWrite(	i++,	0);                     // Addr of the Allocation Vector
	_RamWrite(	i++,	0);

	//

	// figure out the number of the first allocation block
	// after the directory for the phoney allocation block
	// list in _findnext()
	firstBlockAfterDir = 0;
	i = 0x80;

	while (_RamRead(DPBaddr + 9) & i) {
		firstBlockAfterDir++;
		i >>= 1;
	}
	if (_RamRead(DPBaddr + 9) == 0xFF) {
		i = 0x80;

		while (_RamRead(DPBaddr + 10) & i) {
			firstBlockAfterDir++;
			i >>= 1;
		}
	}
	physicalExtentBytes = logicalExtentBytes * (extentMask + 1);
} // _PatchCPM

#ifdef DEBUGLOG
uint8 LogBuffer[128];

void _logRegs(void) {
	uint8 J, I;
	uint8 Flags[9] = {'S', 'Z', '5', 'H', '3', 'P', 'N', 'C'};
	uint8 c = HIGH_REGISTER(AF);

	if ((c < 32) || (c > 126))
		c = 46;

	for (J = 0, I = LOW_REGISTER(AF); J < 8; ++J, I <<= 1)
		Flags[J] = I & 0x80 ? Flags[J] : '.';
	sprintf((char *)LogBuffer, "  BC:%04x DE:%04x HL:%04x AF:%02x(%c)|%s| IX:%04x IY:%04x SP:%04x PC:%04x\n",
			WORD16(BC), WORD16(DE), WORD16(HL), HIGH_REGISTER(AF), c, Flags, WORD16(IX), WORD16(IY), WORD16(SP), WORD16(PC));
	_sys_logbuffer(LogBuffer);
} // _logRegs

void _logMem(uint16 address, uint8 amount) {    // Amount = number of 16 bytes lines, so 1 CP/M block = 8, not 128
	uint8 i, m, c, pos;
	uint8 head = 8;
	uint8 hexa[] = "0123456789ABCDEF";

	for (i = 0; i < amount; ++i) {
		pos = 0;

		for (m = 0; m < head; ++m)
			LogBuffer[pos++] = ' ';
		sprintf((char *)LogBuffer, "  %04x: ", address);

		for (m = 0; m < 16; ++m) {
			c = _RamRead(address++);
			LogBuffer[pos++] = hexa[c >> 4];
			LogBuffer[pos++] = hexa[c & 0x0f];
			LogBuffer[pos++] = ' ';
			LogBuffer[m + head + 48] = c > 31 && c < 127 ? c : '.';
		}
		pos += 16;
		LogBuffer[pos++] = 0x0a;
		LogBuffer[pos++] = 0x00;
		_sys_logbuffer(LogBuffer);
	}
} // _logMem

void _logChar(char *txt, uint8 c) {
	uint8 asc[2];

	asc[0] = c > 31 && c < 127 ? c : '.';
	asc[1] = 0;
	sprintf((char *)LogBuffer, "        %s = %02xh:%3d (%s)\n", txt, c, c, asc);
	_sys_logbuffer(LogBuffer);
} // _logChar

void _logBiosIn(uint8 ch) {
#ifdef LOGBIOS_NOT
	if (ch == LOGBIOS_NOT)
		return;
#endif // ifdef LOGBIOS_NOT
#ifdef LOGBIOS_ONLY
	if (ch != LOGBIOS_ONLY)
		return;
#endif // ifdef LOGBIOS_ONLY
	static const char *BIOSCalls[33] =
	{
		"boot", "wboot", "const", "conin", "conout", "list", "punch/aux", "reader", "home", "seldsk", "settrk", "setsec", "setdma",
		"read", "write", "listst", "sectran", "conost", "auxist", "auxost", "devtbl", "devini", "drvtbl", "multio", "flush", "move",
		"time", "selmem", "setbnk", "xmove", "userf", "reserv1", "reserv2"
	};
	int index = ch / 3;

	if (index < 18) {
		sprintf((char *)LogBuffer, "\nBios call: %3d/%02xh (%s) IN:\n", ch, ch, BIOSCalls[index]);
		_sys_logbuffer(LogBuffer);
	} else {
		sprintf((char *)LogBuffer, "\nBios call: %3d/%02xh IN:\n", ch, ch);
		_sys_logbuffer(LogBuffer);
	}
	_logRegs();
} // _logBiosIn

void _logBiosOut(uint8 ch) {
#ifdef LOGBIOS_NOT
	if (ch == LOGBIOS_NOT)
		return;
#endif // ifdef LOGBIOS_NOT
#ifdef LOGBIOS_ONLY
	if (ch != LOGBIOS_ONLY)
		return;
#endif // ifdef LOGBIOS_ONLY
	sprintf((char *)LogBuffer, "               OUT:\n");
	_sys_logbuffer(LogBuffer);
	_logRegs();
} // _logBiosOut

void _logBdosIn(uint8 ch) {
#ifdef LOGBDOS_NOT
	if (ch == LOGBDOS_NOT)
		return;
#endif // ifdef LOGBDOS_NOT
#ifdef LOGBDOS_ONLY
	if (ch != LOGBDOS_ONLY)
		return;
#endif // ifdef LOGBDOS_ONLY
	uint16 address = 0;
	uint8 size = 0;

	static const char *CPMCalls[41] =
	{
		"System Reset", "Console Input", "Console Output", "Reader Input", "Punch Output", "List Output", "Direct I/O",
		"Get IOByte", "Set IOByte", "Print String", "Read Buffered", "Console Status", "Get Version", "Reset Disk",
		"Select Disk", "Open File", "Close File", "Search First", "Search Next", "Delete File", "Read Sequential",
		"Write Sequential", "Make File", "Rename File", "Get Login Vector", "Get Current Disk", "Set DMA Address",
		"Get Alloc", "Write Protect Disk", "Get R/O Vector", "Set File Attr", "Get Disk Params", "Get/Set User",
		"Read Random", "Write Random", "Get File Size", "Set Random Record", "Reset Drive", "N/A", "N/A",
		"Write Random 0 fill"
	};

	if (ch < 41) {
		sprintf((char *)LogBuffer, "\nBdos call: %3d/%02xh (%s) IN from 0x%04x:\n", ch, ch, CPMCalls[ch], _RamRead16(SP) - 3);
		_sys_logbuffer(LogBuffer);
	} else {
		sprintf((char *)LogBuffer, "\nBdos call: %3d/%02xh IN from 0x%04x:\n", ch, ch, _RamRead16(SP) - 3);
		_sys_logbuffer(LogBuffer);
	}
	_logRegs();

	switch (ch) {
		case 2:
		case 4:
		case 5:
		case 6: {
			_logChar("E", LOW_REGISTER(DE));
			break;
		}

		case 9:
		case 10: {
			address = DE;
			size = 8;
			break;
		}

		case 15:
		case 16:
		case 17:
		case 18:
		case 19:
		case 22:
		case 23:
		case 30:
		case 35:
		case 36: {
			address = DE;
			size = 3;
			break;
		}

		case 20:
		case 21:
		case 33:
		case 34:
		case 40: {
			address = DE;
			size = 3;
			_logMem(address, size);
			sprintf((char *)LogBuffer, "\n");
			_sys_logbuffer(LogBuffer);
			address = dmaAddr;
			size = 8;
			break;
		}

		default: {
			break;
		}
	} // switch
	if (size)
		_logMem(address, size);
} // _logBdosIn

void _logBdosOut(uint8 ch) {
#ifdef LOGBDOS_NOT
	if (ch == LOGBDOS_NOT)
		return;
#endif // ifdef LOGBDOS_NOT
#ifdef LOGBDOS_ONLY
	if (ch != LOGBDOS_ONLY)
		return;
#endif // ifdef LOGBDOS_ONLY
	uint16 address = 0;
	uint8 size = 0;

	sprintf((char *)LogBuffer, "              OUT:\n");
	_sys_logbuffer(LogBuffer);
	_logRegs();

	switch (ch) {
		case 1:
		case 3:
		case 6: {
			_logChar("A", HIGH_REGISTER(AF));
			break;
		}

		case 10: {
			address = DE;
			size = 8;
			break;
		}

		case 20:
		case 21:
		case 33:
		case 34:
		case 40: {
			address = DE;
			size = 3;
			_logMem(address, size);
			sprintf((char *)LogBuffer, "\n");
			_sys_logbuffer(LogBuffer);
			address = dmaAddr;
			size = 8;
			break;
		}

		case 26: {
			address = dmaAddr;
			size = 8;
			break;
		}

		case 35:
		case 36: {
			address = DE;
			size = 3;
			break;
		}

		default: {
			break;
		}
	} // switch
	if (size)
		_logMem(address, size);
} // _logBdosOut
#endif // ifdef DEBUGLOG

void _Bios(void) {
	uint8 ch = LOW_REGISTER(PCX);
	uint8 disk[2] = {'A', 0};

#ifdef DEBUGLOG
	_logBiosIn(ch);
#endif

	switch (ch) {
		case B_BOOT: {
			Status = 1;		// 0 - Ends RunCPM
			break;
		}
		case B_WBOOT: {
			Status = 2;		// 1 - Back to CCP
			break;
		}
		case B_CONST: {		// 2 - Console status
			SET_HIGH_REGISTER(AF, _chready());
			break;
		}
		case B_CONIN: {		// 3 - Console input
			SET_HIGH_REGISTER(AF, _getch());
#ifdef DEBUG
			if (HIGH_REGISTER(AF) == 4)
				Debug = 1;
#endif // ifdef DEBUG
			break;
		}
		case B_CONOUT: {	// 4 - Console output
			_putcon(LOW_REGISTER(BC));
			break;
		}
		case B_LIST: {		// 5 - List output
			break;
		}
		case B_AUXOUT: {    // 6 - Aux/Punch output
			break;
		}
		case B_READER: {    // 7 - Reader input (returns 0x1a = device not implemented)
			SET_HIGH_REGISTER(AF, 0x1a);
			break;
		}
		case B_HOME: {		// 8 - Home disk head
			break;
		}
		case B_SELDSK: {    // 9 - Select disk drive
			disk[0] += LOW_REGISTER(BC);
			HL = 0x0000;
			if (_sys_select(&disk[0]))
				HL = DPHaddr;
			break;
		}
		case B_SETTRK: {    // 10 - Set track number
			break;
		}
		case B_SETSEC: {    // 11 - Set sector number
			break;
		}
		case B_SETDMA: {    // 12 - Set DMA address
			HL = BC;
			dmaAddr = BC;
			break;
		}
		case B_READ: {		// 13 - Read selected sector
			SET_HIGH_REGISTER(AF, 0x00);
			break;
		}
		case B_WRITE: {		// 14 - Write selected sector
			SET_HIGH_REGISTER(AF, 0x00);
			break;
		}
		case B_LISTST: {    // 15 - Get list device status
			SET_HIGH_REGISTER(AF, 0x0ff);
			break;
		}
		case B_SECTRAN: {   // 16 - Sector translate
			HL = BC;		// HL=BC=No translation (1:1)
			break;
		}
		case B_CONOST: {	// 17 - Return status of current screen output device
			SET_HIGH_REGISTER(AF, 0x0ff);
			break;
		}
		case B_AUXIST: {	// 18 - Return status of current auxiliary input device
			SET_HIGH_REGISTER(AF, 0x00);
			break;
		}
		case B_AUXOST: {	// 19 - Return status of current auxiliary output device
			SET_HIGH_REGISTER(AF, 0x00);
			break;
		}
		case B_DEVTBL: {	// 20 - Return the address of the devices table, or 0 if not implemented
			HL = 0x0000;
			break;
		}
		case B_DEVINI: {	// 21 - Reinitialise character device number C
			break;
		}
		case B_DRVTBL: {	// 22 - Return the address of the drive table
			HL = 0x0FFFF;
			break;
		}
		case B_MULTIO: {	// 23 - Notify the BIOS of multi sector transfer
			break;
		}
		case B_FLUSH: {		// 24 - Write any pending data to disc
			SET_HIGH_REGISTER(AF, 0x00);
			break;
		}
		case B_MOVE: {		// 25 - Move a block of memory
			if (!isXmove)
				srcBank = dstBank = curBank;
			while (BC--)
				RAM[HL++ * dstBank] = RAM[DE++ * srcBank];
			isXmove = FALSE;
			break;
		}
		case B_TIME: {		// 26 - Get/Set SCB time
			break;
		}
		case B_SELMEM: {	// 27 - Select memory bank
			curBank = HIGH_REGISTER(AF);
			break;
		}
		case B_SETBNK: {	// 28 - Set the bank to be used for the next read/write sector operation
			ioBank = HIGH_REGISTER(AF);
		}
		case B_XMOVE: {		// 29 - Preload banks for MOVE
			srcBank = LOW_REGISTER(BC);
			dstBank = HIGH_REGISTER(BC);
			isXmove = TRUE;
			break;
		}
		case B_USERF: {		// 30 - This allows programs ending in RET return to internal CCP
			Status = 3;
			break;
		}
		case B_RESERV1:
		case B_RESERV2: {
			break;
		}
		default: {
#ifdef DEBUG    // Show unimplemented BIOS calls only when debugging
			_puts("\r\nUnimplemented BIOS call.\r\n");
			_puts("C = 0x");
			_puthex8(ch);
			_puts("\r\n");
#endif // ifdef DEBUG
			break;
		}
	} // switch
#ifdef DEBUGLOG
	_logBiosOut(ch);
#endif
} // _Bios

void _Bdos(void) {
	uint16 i;
	uint8 j, chr, ch = LOW_REGISTER(BC);

#ifdef DEBUGLOG
	_logBdosIn(ch);
#endif

	HL = 0x0000;                            // HL is reset by the BDOS
	SET_LOW_REGISTER(BC, LOW_REGISTER(DE)); // C ends up equal to E

	switch (ch) {
		/*
		   C = 0 : System reset
		   Doesn't return. Reloads CP/M
		 */
		case P_TERMCPM: {
			Status = 2; // Same as call to "BOOT"
			break;
		}

		/*
		   C = 1 : Console input
		   Gets a char from the console
		   Returns: A=Char
		 */
		case C_READ: {
			HL = _getche();
#ifdef DEBUG
			if (HL == 4)
				Debug = 1;
#endif // ifdef DEBUG
			break;
		}

		/*
		   C = 2 : Console output
		   E = Char
		   Sends the char in E to the console
		 */
		case C_WRITE: {
			_putcon(LOW_REGISTER(DE));
			break;
		}

		/*
		   C = 3 : Auxiliary (Reader) input
		   Returns: A=Char
		 */
		case A_READ: {
			HL = 0x1a;
			break;
		}

		/*
		   C = 4 : Auxiliary (Punch) output
		 */
		case A_WRITE: {
#ifdef USE_PUN
			if (!pun_open) {
				pun_dev = _sys_fopen_w((uint8 *)pun_file);
				pun_open = TRUE;
			}
			if (pun_dev) {
				_sys_fputc(LOW_REGISTER(DE), pun_dev);
			}
#endif // ifdef USE_PUN
			break;
		}

		/*
		   C = 5 : Printer output
		 */
		case L_WRITE: {
#ifdef USE_LST
			if (!lst_open) {
				lst_dev = _sys_fopen_w((uint8 *)lst_file);
				lst_open = TRUE;
			}
			if (lst_dev)
				_sys_fputc(LOW_REGISTER(DE), lst_dev);
#endif // ifdef USE_LST
			break;
		}

		/*
		   C = 6 : Direct console IO
		   E = 0xFF : Checks for char available and returns it, or 0x00 if none (read)
		   ToDo E = 0xFE : Return console input status. Zero if no character is waiting, nonzero otherwise. (CPM3)
		   ToDo E = 0xFD : Wait until a character is ready, return it without echoing. (CPM3)		   
		   E = char : Outputs char (write)
		   Returns: A=Char or 0x00 (on read)
		 */
		case C_RAWIO: {
			if (LOW_REGISTER(DE) == 0xff) {
				HL = _getchNB();
#ifdef DEBUG
				if (HL == 4)
					Debug = 1;
#endif // ifdef DEBUG
			} else {
				_putcon(LOW_REGISTER(DE));
			}
			break;
		}

		/*
		   C = 7 : Get IOBYTE (CPM2)
		   Gets the system IOBYTE
		   Returns: A = IOBYTE (CPM2)
		   ToDo REPLACE with
		   C = 7 : Auxiliary Input status (CPM3)
		   0FFh is returned if the Auxiliary Input device has a character ready; otherwise 0 is returned.
		   Returns: A=0 or 0FFh (CPM3)
		 */
		case A_STATIN: {
			HL = _RamRead(0x0003);
			break;
		}

		/*
		   C = 8 : Set IOBYTE (CPM2)
		   E = IOBYTE
		   Sets the system IOBYTE to E
		   ToDo REPLACE with
		   C = 8 : Auxiliary Output status (CPM3)
		   0FFh is returned if the Auxiliary Output device is ready for characters; otherwise 0 is returned.
		   Returns: A=0 or 0FFh (CPM3)
		 */
		case A_STATOUT: {
			_RamWrite(0x0003, LOW_REGISTER(DE));
			break;
		}

		/*
		   C = 9 : Output string
		   DE = Address of string
		   Sends the $ terminated string pointed by (DE) to the screen
		 */
		case C_WRITESTR: {
			while ((ch = _RamRead(DE++)) != '$')
				_putcon(ch);
			break;
		}

		/*
		   C = 10 (0Ah) : Buffered input
		   DE = Address of buffer
		   ToDo DE = 0 Use DMA address (CPM3) AND
		   DE=address:			DE=0:
			buffer: DEFB    size        buffer: DEFB    size
			        DEFB    ?                   DEFB    len
			        	bytes           	    bytes
		   Reads (DE) bytes from the console
		   Returns: A = Number of chars read
		   DE) = First char
		 */
		case C_READSTR: {
            uint16 chrsMaxIdx = WORD16(DE);                 //index to max number of characters
            uint16 chrsCntIdx = (chrsMaxIdx + 1) & 0xFFFF;  //index to number of characters read
            uint16 chrsIdx = (chrsCntIdx + 1) & 0xFFFF;     //index to characters
            //printf("\n\r chrsMaxIdx: %0X, chrsCntIdx: %0X", chrsMaxIdx, chrsCntIdx);

            static uint8 *last = 0;
            if (!last)
                last = (uint8*)calloc(1,256);    //allocate one (for now!)

#ifdef PROFILE
			if (time_start != 0) {
				time_now = millis();
				printf(": %ld\n", time_now - time_start);
				time_start = 0;
			}
#endif // ifdef PROFILE
            uint8 chrsMax = _RamRead(chrsMaxIdx);   // Gets the max number of characters that can be read
            uint8 chrsCnt = 0;                      // this is the number of characters read
            uint8 curCol = 0;                       //this is the cursor column (relative to where it started)

            while (chrsMax) {
                // pre-backspace, retype & post backspace counts
                uint8 preBS = 0, reType = 0, postBS = 0;

                chr = _getch(); //input a character

                if (chr == 1) {                             // ^A - Move cursor one character to the left
                    if (curCol > 0) {
                        preBS++;            //backspace one
                    } else {
                        _putcon('\007');    //ring the bell
                    }
                }

                if (chr == 2) {                             // ^B - Toggle between beginning & end of line
                    if (curCol) {
                        preBS = curCol;             //move to beginning
                    } else {
                        reType = chrsCnt - curCol;  //move to EOL
                    }
                }

                if ((chr == 3) && (chrsCnt == 0)) {         // ^C - Abort string input
                    _puts("^C");
                    Status = 2;
                    break;
                }

#ifdef DEBUG
                if (chr == 4) {                             // ^D - DEBUG
                    Debug = 1;
					break;
                }
#endif // ifdef DEBUG

                if (chr == 5) {                             // ^E - goto beginning of next line
                    _putcon('\n');
                    preBS = curCol;
                    reType = postBS = chrsCnt;
                }

                if (chr == 6) {                             // ^F - Move the cursor one character forward
                    if (curCol < chrsCnt) {
                        reType++;
                    } else {
                        _putcon('\007');  //ring the bell
                    }
                }

                if (chr == 7) {                             // ^G - Delete character at cursor
                    if (curCol < chrsCnt) {
                        //delete this character from buffer
                        for (i = curCol, j = i + 1; j < chrsCnt; i++, j++) {
                            ch = _RamRead(((chrsIdx + j) & 0xFFFF));
                            _RamWrite((chrsIdx + i) & 0xFFFF, ch);
                        }
                        reType = postBS = chrsCnt - curCol;
                        chrsCnt--;
                    } else {
                        _putcon('\007');  //ring the bell
                    }
                }

                if (((chr == 0x08) || (chr == 0x7F))) {     // ^H and DEL - Delete one character to left of cursor
                    if (curCol > 0) {   //not at BOL
                        if (curCol < chrsCnt) { //not at EOL
                            //delete previous character from buffer
                            for (i = curCol, j = i - 1; i < chrsCnt; i++, j++) {
                                ch = _RamRead(((chrsIdx + i) & 0xFFFF));
                                _RamWrite((chrsIdx + j) & 0xFFFF, ch);
                            }
                            preBS++;    //pre-backspace one
                            //note: does one extra to erase EOL
                            reType = postBS = chrsCnt - curCol + 1;
                        } else {
                            preBS = reType = postBS = 1;
                        }
                        chrsCnt--;
                    } else {
                        _putcon('\007');  //ring the bell
                    }
                }

                if ((chr == 0x0A) || (chr == 0x0D)) {   // ^J and ^M - Ends editing
#ifdef PROFILE
                    time_start = millis();
#endif
                    break;
                }

                if (chr == 0x0B) {                      // ^K - Delete to EOL from cursor
                    if (curCol < chrsCnt) {
                        reType = postBS = chrsCnt - curCol;
                        chrsCnt = curCol;   //truncate buffer to here
                    } else {
                        _putcon('\007');  //ring the bell
                    }
                }

                if (chr == 18) {                        // ^R - Retype the command line
                    _puts("#\b\n");
                    preBS = curCol;             //backspace to BOL
                    reType = chrsCnt;           //retype everything
                    postBS = chrsCnt - curCol;  //backspace to cursor column
                }

                if (chr == 21) {                        // ^U - delete all characters
                    _puts("#\b\n");
                    preBS = curCol; //backspace to BOL
                    chrsCnt = 0;
                }

                if (chr == 23) {                        // ^W - recall last command
                    if (!curCol) {      //if at beginning of command line
                        uint8 lastCnt = last[0];
                        if (lastCnt) {  //and there's a last command
                            //restore last command
                            for (j = 0; j <= lastCnt; j++) {
                                _RamWrite((chrsCntIdx + j) & 0xFFFF, last[j]);
                            }
                            //retype to greater of chrsCnt & lastCnt
                            reType = (chrsCnt > lastCnt) ? chrsCnt : lastCnt;
                            chrsCnt = lastCnt;  //this is the restored length
                            //backspace to end of restored command
                            postBS = reType - chrsCnt;
                        } else {
                            _putcon('\007');  //ring the bell
                        }
                    } else if (curCol < chrsCnt) {  //if not at EOL
                        reType = chrsCnt - curCol;  //move to EOL
                    }
                }

                if (chr == 24) {                        // ^X - delete all character left of the cursor
                    if (curCol > 0) {
                        //move rest of line to beginning of line
                        for (i = 0, j = curCol; j < chrsCnt;i++, j++) {
                            ch = _RamRead(((chrsIdx + j) & 0xFFFF));
                            _RamWrite((chrsIdx +i) & 0xFFFF, ch);
                        }
                        preBS = curCol;
                        reType = chrsCnt;
                        postBS = chrsCnt;
                        chrsCnt -= curCol;
                    } else {
                        _putcon('\007');  //ring the bell
                    }
                }

                if ((chr >= 0x20) && (chr <= 0x7E)) { //valid character
                    if (curCol < chrsCnt) {
                        //move rest of buffer one character right
                        for (i = chrsCnt, j = i - 1; i > curCol; i--, j--) {
                            ch = _RamRead(((chrsIdx + j) & 0xFFFF));
                            _RamWrite((chrsIdx + i) & 0xFFFF, ch);
                        }
                    }
                    //put the new character in the buffer
                    _RamWrite((chrsIdx + curCol) & 0xffff, chr);

                    chrsCnt++;
                    reType = chrsCnt - curCol;
                    postBS = reType - 1;
                }

                //pre-backspace
                for (i = 0; i < preBS; i++) {
                    _putcon('\b');
                    curCol--;
                }

                //retype
                for (i = 0; i < reType; i++) {
                    if (curCol < chrsCnt) {
                        ch = _RamRead(((chrsIdx + curCol) & 0xFFFF));
                    } else {
                        ch = ' ';
                    }
                    _putcon(ch);
                    curCol++;
                }

                //post-backspace
                for (i = 0; i < postBS; i++) {
                    _putcon('\b');
                    curCol--;
                }

                if (chrsCnt == chrsMax)   // Reached the maximum count
                    break;
            }   // while (chrsMax)

            // Save the number of characters read
            _RamWrite(chrsCntIdx, chrsCnt);

            //if there are characters...
            if (chrsCnt) {
                //... then save this as last command
                for (j = 0; j <= chrsCnt; j++) {
                    last[j] = _RamRead((chrsCntIdx + j) & 0xFFFF);
                }
            }
#if 0
            printf("\n\r chrsMaxIdx: %0X, chrsMax: %u, chrsCnt: %u", chrsMaxIdx, chrsMax, chrsCnt);
            for (j = 0; j < chrsCnt + 2; j++) {
                printf("\n\r chrsMaxIdx[%u]: %0.2x", j, last[j]);
            }
#endif
            _putcon('\r');          // Gives a visual feedback that read ended
			break;
		}

		/*
		   C = 11 (0Bh) : Get console status
		   Returns: A=0x00 or 0xFF
		 */
		case C_STAT: {
			HL = _chready();
			break;
		}

		/*
		   C = 12 (0Ch) : Get version number
		   Returns: B=H=system type, A=L=version number
		 */
		case S_BDOSVER: {
			HL = 0x22;
			break;
		}

		/*
		   C = 13 (0Dh) : Reset disk system
		 */
		case DRV_ALLRESET: {
			roVector = 0;       // Make all drives R/W
			loginVector = 0;
			dmaAddr = 0x0080;
			cDrive = 0;         // userCode remains unchanged
			HL = _CheckSUB();   // Checks if there's a $$$.SUB on the boot disk
			break;
		}

		/*
		   C = 14 (0Eh) : Select Disk
		   Returns: A=0x00 or 0xFF
		 */
		case DRV_SET: {
			oDrive = cDrive;
			cDrive = LOW_REGISTER(DE);
			HL = _SelectDisk(LOW_REGISTER(DE) + 1); // +1 here is to allow SelectDisk to be used directly by disk.h as well
			if (!HL) {
				oDrive = cDrive;
			} else {
				if ((_RamRead(DSKByte) & 0x0f) == cDrive) {
					cDrive = oDrive = 0;
					_RamWrite(DSKByte, _RamRead(DSKByte) & 0xf0);
				} else {
					cDrive = oDrive;
				}
			}
			break;
		}

		/*
		   C = 15 (0Fh) : Open file
		   Returns: A=0x00 or 0xFF
		 */
		case F_OPEN: {
			HL = _OpenFile(DE);
			break;
		}

		/*
		   C = 16 (10h) : Close file
		 */
		case F_CLOSE: {
			HL = _CloseFile(DE);
			break;
		}

		/*
		   C = 17 (11h) : Search for first
		 */
		case F_SFIRST: {
			HL = _SearchFirst(DE, TRUE);    // TRUE = Creates a fake dir entry when finding the file
			break;
		}

		/*
		   C = 18 (12h) : Search for next
		 */
		case F_SNEXT: {
			HL = _SearchNext(DE, TRUE); // TRUE = Creates a fake dir entry when finding the file
			break;
		}

		/*
		   C = 19 (13h) : Delete file
		 */
		case F_DELETE: {
			HL = _DeleteFile(DE);
			break;
		}

		/*
		   C = 20 (14h) : Read sequential
		   DE = address of FCB
		   ToDo under CP/M 3 this can be a multiple of 128 bytes
		   Returns: A = return code
		 */
		case F_READ: {
			HL = _ReadSeq(DE);
			break;
		}

		/*
		   C = 21 (15h) : Write sequential
		   DE = address of FCB
		   ToDo under CP/M 3 this can be a multiple of 128 bytes
		   Returns: A=return code
		   */
		case F_WRITE: {
			HL = _WriteSeq(DE);
			break;
		}

		/*
		   C = 22 (16h) : Make file
		 */
		case F_MAKE: {
			HL = _MakeFile(DE);
			break;
		}

		/*
		   C = 23 (17h) : Rename file
		 */
		case F_RENAME: {
			HL = _RenameFile(DE);
			break;
		}

		/*
		   C = 24 (18h) : Return log-in vector (active drive map)
		 */
		case DRV_LOGINVEC: {
			HL = loginVector;   // (todo) improve this
			break;
		}

		/*
		   C = 25 (19h) : Return current disk
		 */
		case DRV_GET: {
			HL = cDrive;
			break;
		}

		/*
		   C = 26 (1Ah) : Set DMA address
		 */
		case F_DMAOFF: {
			dmaAddr = DE;
			break;
		}

		/*
		   C = 27 (1Bh) : Get ADDR(Alloc)
		 */
		case DRV_ALLOCVEC: {
			HL = SCBaddr;
			break;
		}

		/*
		   C = 28 (1Ch) : Write protect current disk
		 */
		case DRV_SETRO: {
			roVector = roVector | (1 << cDrive);
			break;
		}

		/*
		   C = 29 (1Dh) : Get R/O vector
		 */
		case DRV_ROVEC: {
			HL = roVector;
			break;
		}

		/*
		   C = 30 (1Eh) : Set file attributes (does nothing)
		 */
		case F_ATTRIB: {
			HL = 0;
			break;
		}

		/*
		   C = 31 (1Fh) : Get ADDR(Disk Parms)
		 */
		case DRV_PDB: {
			HL = DPBaddr;
			break;
		}

		/*
		   C = 32 (20h) : Get/Set user code
		 */
		case F_USERNUM: {
			if (LOW_REGISTER(DE) == 0xFF) {
				HL = userCode;
			} else {
				_SetUser(DE);
			}
			break;
		}

		/*
		   C = 33 (21h) : Read random
		   ToDo under CPM3, if A returns 0xFF, H returns hardware error 
		 */
		case F_READRAND: {
			HL = _ReadRand(DE);
			break;
		}

		/*
		   C = 34 (22h) : Write random
		   ToDo under CPM3, if A returns 0xFF, H returns hardware error 
		   */
		case F_WRITERAND: {
			HL = _WriteRand(DE);
			break;
		}

		/*
		   C = 35 (23h) : Compute file size
		 */
		case F_SIZE: {
			HL = _GetFileSize(DE);
			break;
		}

		/*
		   C = 36 (24h) : Set random record
		 */
		case F_RANDREC: {
			HL = _SetRandom(DE);
			break;
		}

		/*
		   C = 37 (25h) : Reset drive
		 */
		case DRV_RESET: {
			roVector = roVector & ~DE;
			break;
		}

		/* ********* Function 38: Not supported by CP/M 2.2 *********
		  ********* Function 39: Not supported by CP/M 2.2 *********
		  ********* (todo) Function 40: Write random with zero fill *********
		 */
		
		/*
		  ToDo C = 38 (26h) : Access drives (CPM3)
		    This is an MP/M function that is not supported under CP/M 3. If called, the file
		     system returns a zero In register A indicating that the access request is successful.
		 */		
		case DRV_ACCESS: {
			break;
		}			

		/*
		  ToDo C = 39 (27h) : Free drives (CPM3)
		    This is an MP/M function that is not supported under CP/M 3. If called, the file
		     system returns a zero In register A indicating that the access request is successful.
		 */		
		case DRV_FREE: {
			break;
		}			

		/*
		   C = 40 (28h) : Write random with zero fill (we have no disk blocks, so just write random)
		   DE = address of FCB
		   Returns: A = return code
		   	    H = Physical Error
		 */
		case F_WRITEZF: {
			HL = _WriteRand(DE);
			break;
		}

		/* 
		   ToDo: C = 41 (29h) : Test and Write Record (CPM3)
		   DE = address of FCB
		   Returns: A = return code
		   	    H = Physical Error
		 */
		case F_TESTWRITE: {
			break;
		}

		/* 
		   ToDo: C = 42 (2Ah) : Lock Record (CPM3)
		   DE = address of FCB
		   Returns: A = return code
		   	    H = Physical Error
		 */
		case F_LOCKFILE: {
			break;
		}

		/* 
		   ToDo: C = 43 (2Bh) : Unlock Record (CPM3)
		   DE = address of FCB
		   Returns: A = return code
		   	    H = Physical Error
		 */
		case F_UNLOCKFILE: {
			break;
		}


		/* 
		   ToDo: C = 44 (2Ch) : Set number of records to read/write at once (CPM3)
		   E = Number of Sectors
		   Returns: A = return code (Returns A=0 if E was valid, 0FFh otherwise)
		 */
		case F_MULTISEC: {
			break;
		}

		/* 
		   ToDo: C = 45 (2Dh) : Set BDOS Error Mode (CPM3)
		   E = BDOS Error Mode
		   E < 254 Compatibility mode; program is terminated and an error message printed.
		   E = 254 Error code is returned in H, error message is printed.
		   E = 255 Error code is returned in H, no error message is printed.
		   Returns: None
		 */
		case F_ERRMODE: {
			break;
		}

		/* 
		   ToDo: C = 46 (2Eh) : Get Free Disk Space (CPM3)
		   E = Drive
		   Returns: A = return code
		   	    H = Physical Error
			    Binary result in the first 3 bytes of current DMA buffer
		 */
		case DRV_SPACE: {
			break;
		}

		/* 
		   ToDo: C = 47 (2Fh) : Chain to program (CPM3)
		   E = Chain flag
		   Returns: None
		 */
		case P_CHAIN: {
			break;
		}

		/* 
		   ToDo: C = 48 (30h) : Flush Bufers (CPM3)
		   E = Purge flag
		   Returns: A = return code
		   	    H = Physical Error
		 */
		case DRV_FLUSH: {
			break;
		}

		/* 
		   ToDo: C = 49 (31h) : Get/Set System Control (CPM3)
		   DE = SCB PB Address
		   Returns: A = Returned Byte
		   	    HL = Returned Word
		 */
		case S_SCB: {
			break;
		}


		/* 
		   ToDo: C = 50 (32h) : Direct BIOS Calls (CPM3)
		   DE = BIOS PB Address
		   Returns:  BIOS Return
		 */
		case S_BIOS: {
			break;
		}

		/* 
		   ToDo: C = 59 (3Bh) : Load Overlay (CPM3)
		   DE = address of FCB
		   Returns: A = return code
		   	    H = Physical Error
		 */
		case P_LOAD: {
			break;
		}


		/* 
		   ToDo: C = 60 (3Ch) : Call Resident System Extension (RSX) (CPM3)
		   DE =  RSX PB Address
		   Returns: A = return code
		   	    H = Physical Error
		 */
		case S_RSX: {
			break;
		}


		/* 
		   ToDo: C = 98 (62h) : Free Blocks (CPM3)
		   Returns: A = return code
		   	    H = Physical Error
		 */
		case F_CLEANUP: {
			break;
		}


		/* 
		   ToDo: C = 99 (63h) : Truncate File (CPM3)
		   DE = address of FCB
		   Returns: A = Directory code
		   	    H = Extended or Physical Error
		 */
		case F_TRUNCATE: {
			break;
		}


		/* 
		   ToDo: C = 100 (64h) : Set Directory Label (CPM3)
		   DE = address of FCB
		   Returns: A = Directory code
		   	    H = Extended or Physical Error
		 */
		case DRV_SETLABEL: {
			break;
		}


		/* 
		   ToDo: C = 101 (65h) : Return Directory Label Data (CPM3)
		   E = Drive
		   Returns: A = Directory Label Data Byte or 0xFF
		   	    H = Physical Error
		 */
		case DRV_GETLABEL: {
			break;
		}


		/* 
		   ToDo: C = 102 (66h) : Read File Date Stamps and Password Mode (CPM3)
		   DE = address of FCB
		   Returns: A = Directory code
		   	    H = Physical Error
		 */
		case F_TIMEDATE: {
			break;
		}


		/* 
		   ToDo: C = 103 (67h) : Write File XFCB (CPM3)
		   DE = address of FCB
		   Returns: A = Directory code
		   	    H = Physical Error
		 */
		case F_WRITEXFCB: {
			break;
		}


		/* 
		   ToDo: C = 104 (68h) : Set Date and Time (CPM3)
		   DE = Date and Time (DAT) Address
		   Returns: None
		 */
		case T_SET: {
			break;
		}


		/* 
		   ToDo: C = 105 (69h) : Get Date and Time (CPM3)
		   DE = Date and Time (DAT) Address
		   Returns: Date and Time (DAT) set
		   	    A = Seconds (in packed BCD format)
		 */
		case T_GET: {
			break;
		}


		/* 
		   ToDo: C = 106 (6Ah) : Set Default Password (CPM3)
		   DE = Password Addresss
		   Returns: None
		 */
		case F_PASSWD: {
			break;
		}


		/* 
		   ToDo: C = 107 (6Bh) : Return Serial Number (CPM3)
		   DE = Serial Number Field
		   Returns: Serial number field set
		 */
		case S_SERIAL: {
			break;
		}


		/* 
		   ToDo: C = 108 (6Ch) : Get/Set Program Return Code (CPM3)
		   DE =  0xFFFF (Get) or Program Return Code (Set)
		   Returns: HL = Program Return Code or (none)
		 */
		case P_CODE: {
			break;
		}


		/* 
		   ToDo: C = 109 (6Dh) : Get/Set Console Mode (CPM3)
		   DE =  0xFFFF (Get) or Console Mode (Set)
		   Returns: HL = Console Mode or (none)
		 */
		case C_MODE: {
			break;
		}


		/* 
		   ToDo: C = 110 (6Eh) : Get/Set Output Delimiter (CPM3)
		   DE =  0xFFFF (Get) or E = Delimiter (Set)
		   Returns: A = Output Delimiter or (none)
		 */
		case C_DELIMIT: {
			break;
		}


		/* 
		   ToDo: C = 111 (6Fh) : Print Block (CPM3)
		   DE =  address of CCB
		   Returns: None
		 */
		case C_WRITEBLK: {
			break;
		}


		/* 
		   ToDo: C = 112 (70h) : List Block (CPM3)
		   DE =  address of CCB
		   Returns: None
		 */
		case L_WRITEBLK: {
			break;
		}


		/* 
		   ToDo: C = 152 (98h) : List Block (CPM3)
		   DE =  address of PFCB
		   Returns: HL = Return code
		   	    Parsed file control block
		 */
		case F_PARSE: {
			break;
		}


#if defined board_digital_io

		/*
		   C = 220 (DCh) : PinMode
		 */
		case 220: {
			pinMode(HIGH_REGISTER(DE), LOW_REGISTER(DE));
			break;
		}

		/*
		   C = 221 (DDh) : DigitalRead
		 */
		case 221: {
			HL = digitalRead(HIGH_REGISTER(DE));
			break;
		}

		/*
		   C = 222 (DEh) : DigitalWrite
		 */
		case 222: {
			digitalWrite(HIGH_REGISTER(DE), LOW_REGISTER(DE));
			break;
		}

		/*
		   C = 223 (DFh) : AnalogRead
		 */
		case 223: {
			HL = analogRead(HIGH_REGISTER(DE));
			break;
		}

#endif // if defined board_digital_io
#if defined board_analog_io

		/*
		   C = 224 (E0h) : AnalogWrite
		 */
		case 224: {
			analogWrite(HIGH_REGISTER(DE), LOW_REGISTER(DE));
			break;
		}

#endif // if defined board_analog_io

		/*
		   C = 230 (E6h) : Set 8 bit masking
		 */
		case 230: {
			mask8bit = LOW_REGISTER(DE);
			break;
		}

		/*
		   C = 231 (E7h) : Host specific BDOS call
		 */
		case 231: {
			HL = hostbdos(DE);
			break;
		}

			/*
			   C = 232 (E8h) : ESP32 specific BDOS call
			 */
#if defined board_esp32
		case 232: {
			HL = esp32bdos(DE);
			break;
		}

#endif // if defined board_esp32
#if defined board_stm32
		case 232: {
			HL = stm32bdos(DE);
			break;
		}

#endif // if defined board_stm32

		/*
		   C = 249 (F9h) : MakeDisk
		   Makes a disk directory if not existent.
		 */
		case 249: {
			HL = _MakeDisk(DE);
			break;
		}

		/*
		   C = 250 (FAh) : HostOS
		   Returns: A = 0x00 - Windows / 0x01 - Arduino / 0x02 - Posix / 0x03 - Dos / 0x04 - Teensy / 0x05 - ESP32 / 0x06 - STM32
		 */
		case 250: {
			HL = HostOS;
			break;
		}

		/*
		   C = 251 (FBh) : Version
		   Returns: A = 0xVv - Version in BCD representation: V.v
		 */
		case 251: {
			HL = VersionBCD;
			break;
		}

		/*
		   C = 252 (FCh) : CCP version
		   Returns: A = 0x00-0x04 = DRI|CCPZ|ZCPR2|ZCPR3|Z80CCP / 0xVv = Internal version in BCD: V.v
		 */
		case 252: {
			HL = VersionCCP;
			break;
		}

		/*
		   C = 253 (FDh) : CCP address
		 */
		case 253: {
			HL = CCPaddr;
			break;
		}

#ifdef HASLUA

		/*
		   C = 254 (FEh) : Run Lua file
		 */
		case 254: {
			HL = _RunLua(DE);
			break;
		}

#endif // ifdef HASLUA

		/*
		   Unimplemented calls get listed
		 */
		default: {
#ifdef DEBUG    // Show unimplemented BDOS calls only when debugging
			_puts("\r\nUnimplemented BDOS call.\r\n");
			_puts("C = 0x");
			_puthex8(ch);
			_puts("\r\n");
#endif // ifdef DEBUG
			break;
		}
	} // switch

	// CP/M BDOS does this before returning
	SET_HIGH_REGISTER(	BC, HIGH_REGISTER(HL));
	SET_HIGH_REGISTER(	AF, LOW_REGISTER(HL));

#ifdef DEBUGLOG
	_logBdosOut(ch);
#endif
} // _Bdos

#endif // ifndef CPM_H
