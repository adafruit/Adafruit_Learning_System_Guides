// Speak & Spell sound board for the Adafruit NeoTrellis M4.
// Requires the following libraries, install with Arduino Library Manager:
//  - Adafruit_NeoTrellisM4
//  - Adafruit_Keypad
//  - Adafruit_NeoPixel
// Also requires the Adafruit fork of the Talkie library, install manually:
//  - https://github.com/adafruit/Talkie
//
// Connect headphones or speaker to the Trellis audio output.
// Tap buttons to hear letters, numbers, words and phrases. Hold one of the
// bottom row buttons to enable one of eight sets of 31 sounds (plus the 24
// sounds when no bottom-row button is held).
// What you're hearing are not simply WAV files. Instead, the Talkie library
// emulates the TMS5100 speech chip used in the original Speak & Spell.
// File words.h contains a selection of speech data exactly as it was stored
// in the original ROM in a highly-compressed lossy format called LPC-10.

#include <Adafruit_NeoTrellisM4.h>
#include <talkie.h>
#include "words.h"

Adafruit_NeoTrellisM4 trellis;
Talkie                voice;

// These tables assign sounds to each button. These are just pointers to
// sound data in the file words.h, or NULL where no sound is assigned.
// There are 9 goups of 32 buttons, the first is with none of the 8
// bottom-row "shift" buttons held, the other 8 groups are for each of
// the 8 shifted states. 
const uint8_t *sound[9][32] = {
  { sp0 , sp1 , sp2 , sp3 , sp4 , sp5 , sp6 , sp7 ,
    sp8 , sp9 , spTEN, spABOVE, spACHIEVE, spAGAINST, spALMOST, spALREADY, 
    spANCIENT, spANOTHER, spANSWER, spANYTHING, spAPPROVE, spBEAUTY, spBELIEVE, spBOULDER,
    NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL }, // "Shift" keys, leave this row NULL
  { spBROTHER, spBUILT, spBULLET, spBULLETIN, spBUREAU, spBUSHEL, spBUSINESS, spCARAVAN,
    spCARRY, spCHALK, spCHILD, spCIRCUIT, spCLEANSER, spCOLOR, spCOMFORT, spCOMING,
    spCONQUER, spCORRECT, spCOULDNT, spCOUNTRY, spCOUPLE, spCOURAGE, spCOUSIN, spDISCOVER,
    NULL, spDOES, spDOZEN, spDUNGEON, spEARLY, spEARNEST, spEARTH, spECHO },
  { spEGG, spENOUGH, spERROR, spEVERY, spEVERYONE, spEXTRA, spEYEBROW, spFEATHER,
    spFIELD, spFINGER, spFIRED, spFLOOD, spFLOOR, spFREIGHT, spFRONT, spGARAGE,
    spGLACIER, spGLOVE, spGREATER, spGUARD, spGUESS, spGUIDE, spHALF, spHASTE,
    spHEALTH, NULL, spHEALTHY, spHEAVY, spHEROES, spHONEY, spHONOR, spHOSTESS },
  { spHYGIENE, spIMPROVE, spINSTEAD, spIRON, spIS, spISLAND, spISLE, spJOURNEY,
    spKEY, spLANGUAGE, spLAUGH, spLAUGHTER, spLEARN, spLEATHER, spLEISURE, spLETTUCE,
    spLIBRARY, spLINGER, spLOSE, spMACHINE, spMEADOW, spMEANING, spMEASURE, spMECHANIC,
    spMILD, spMINUTE, NULL, spMIRROR, spMISTAKE, spMONEY, spMOSQUITO, spMOST },
  { spMOTHER, spMOVIE, spMUSTACHE, spNARROW, spNEIGHBOR, spNUISANCE, spOCEAN, spONCE,
    spONION, spOTHER, spOUTDOOR, spOVEN, spPERIOD, spPIANOS, spPIERCE, spPINT,
    spPLAGUE, spPLEASANT, spPLEASURE, spPLUNGER, spPLURAL, spPOSTAGE, spPOULTRY, spPRETTY,
    spPROMISE, spPULL, spPUSH, NULL, spQUESTION, spQUIET, spQUOTIENT, spRANGE },
  { spRANGER, spREADY, spREINDEER, spRELIEF, spRELIEVE, spREMOVE, spRHYTHM, spROCK,
    spRURAL, spSAYS, spSCHEDULE, spSCHOOL, spSCISSORS, spSEARCH, spSERIOUS, spSHIELD,
    spSHOULD, spSHOULDER, spSHOVEL, spSIGN, spSKI, spSOMEONE, spSOMETIME, spSOURCE,
    spSPELL, spSPONGE, spSPREAD, spSQUAD, NULL, spSQUASH, spSQUAT, spSTATUE },
  { spSTOMACH, spSTRANGER, spSUGAR, spSURE, spSURGEON, spSWAMP, spSWAN, spSWAP,
    spSWEAT, spSWEATER, spTALK, spTODAY, spTOMORROW, spTON, spTONGUE, spTOUCH,
    spTOUGH, spTOWARD, spTREASURE, spTRY, spUNCOVER, spUNION, spUSUAL, spVIEW,
    spWALK, spWARM, spWAS, spWASH, spWATCH, NULL, spWATER, spWEALTH },
  { spWEIRD, spWELCOME, spWILD, spWOLVES, spWOMAN, spWONDER, spWORD, spWORLD,
    spWORTH, spWRONG, spYIELD, spYOLK, spYOUNG, spYOURSELF, spZEROS, spHERE_IS_YOUR_SCORE,
    spI_WIN, spNEXT_SPELL, spNOW_SPELL, spNOW_TRY, spPERFECT_SCORE, spSAY_IT, spTHAT_IS_CORRECT, spTHAT_IS_INCORRECT,
    spTHAT_IS_RIGHT, spTHE_CORRECT_SPELLING_OF, spTO_WED, spTRY_AGAIN, spYOU_ARE_CORRECT, spYOU_ARE_RIGHT, NULL, spYOU_WIN },
  { spA , spB , spC , spD , spE , spF , spG , spH ,
    spI , spJ , spK , spL , spM , spN , spO , spP ,
    spQ , spR , spS , spT , spU , spV , spW , spX ,
    spY , spZ , spAPOSTROPHE , spBEEPS_1 , spBEEPS_2 , spBEEPS_3 , spBEEPS_4, NULL } };

uint8_t shiftmode = 0; // Which of 8 shift buttons is held (0 = none)

// Lights the bottom-most row of buttons in the "ready for input" pattern
void idle(void) {
  trellis.fill(0);
  for(int i=0; i<8; i++) {
    trellis.setPixelColor(24 + i, trellis.ColorHSV(i * 65536 / 8, 255, 6));
  }
}

// SETUP FUNCTION - RUNS ONCE AT STARTUP ***********************************

void setup() {
  trellis.begin();

  // You MUST call this function before issuing Speak & Spell data to the
  // Talkie library. By default, that library emulates the TMS5220, a later
  // speech chip (used in the TI-99/4A and others) that uses a slightly
  // different data format. This puts it in TMS5100-compatible mode:
  voice.mode(TALKIE_TMS5100);

  idle(); // Light Trellis buttons in the "ready for input" pattern
}

// LOOP FUNCTION - AFTER SETUP, RUNS REPEATEDLY ****************************

void loop() {
  trellis.tick();                                 // Generate button events
  while(trellis.available()) {                    // Process each event...
    keypadEvent e = trellis.read();
    if(e.bit.EVENT == KEY_JUST_PRESSED) {         // Button press?
      if(shiftmode || (e.bit.KEY < 24)) {         // If not a shift-button
        if(sound[shiftmode][e.bit.KEY] != NULL) { // and has word assigned,
          voice.say(sound[shiftmode][e.bit.KEY], false); // Say it!
        }
      } else {                                    // Is a shift-button
        shiftmode = e.bit.KEY - 23;               // shiftmode = 1 to 8
        trellis.fill(trellis.ColorHSV((shiftmode-1) * 65536 / 8, 255, 2));
      }
    } else if(e.bit.EVENT == KEY_JUST_RELEASED) { // Button release?
      if(e.bit.KEY == (shiftmode + 23)) {         // Shift mode button?
        shiftmode = 0;                            // Un-shift
        idle();                                   // Restore 'ready' lights
      }
    }
  }
}
