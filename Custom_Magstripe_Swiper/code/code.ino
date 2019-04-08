#define PIEZO 3
#define CLOCK2 10
#define DATA2 9
#define CARD2 23

#define TRACK1_LEN 79
#define BUFF 30
uint8_t track1[TRACK1_LEN+BUFF];
uint8_t scratch[TRACK1_LEN+BUFF];

#define RIGHT 1
#define LEFT 0

#define BYTELENGTH 7 // 6 + 1 parity

//#define _SERIAL 1
#define _KEYBOARD 1

void beep(uint8_t pin, long freq, long dur) {
  long d = 500000/ freq;

  for (long i=0; i< freq * dur / 2000; i++) {
    digitalWrite(pin, HIGH);
    delayMicroseconds(d);
    digitalWrite(pin, LOW);
    delayMicroseconds(d);
  }  
}


void setup()
{
#ifdef _SERIAL
  Serial.begin(9600); // USB is always 12 Mbit/sec
#endif
 
  pinMode(5, OUTPUT);
  pinMode(PIEZO, OUTPUT);
  digitalWrite(5, LOW);
  
  beep(PIEZO, 4000, 200);
}

//http://stripesnoop.sourceforge.net/devel/magtek-app.pdf

void loop()
{
  while (digitalRead(CARD2));
  uint8_t zeros = 0;
  
  // card was swiped!
  // check clocked in data
  for (uint8_t t1 = 0; t1 < TRACK1_LEN; t1++) {
    track1[t1] = 0;
    for (uint8_t b=0; b < BYTELENGTH; b++) {

      // wait while clock is high
      while (digitalRead(CLOCK2) && !digitalRead(CARD2));
      // we sample on the falling edge!
      uint8_t x = digitalRead(DATA2);
      if (!x) {
      // data is LSB and inverted!
        track1[t1] |= _BV(b);
      }
      // heep hanging out while its low
      while (!digitalRead(CLOCK2) && !digitalRead(CARD2));
     
    }
    
    if ((t1 == 0) && (track1[t1] == 0)) {
     // get rid of leading 0's
     zeros++;
     t1--;
     continue;
    }
    
    if (zeros < 4) {
      t1--;
     continue;
    }
    if ((t1 == 1) && (track1[t1] == 0)) {
     t1 = -1;
     zeros = 1;
     continue;
    }
  }
  
  // shift left until we have no more starting zero bits!
  while ((track1[0] & 0x1) == 0 ) {
    shifttrack(track1, scratch, LEFT);
  }

  if (!verifycard(track1)) {
    // Serial.println("flippy?");
    
    // didnt pass verification, perhaps we can try flipping it around?
    for (uint8_t i = 0; i < TRACK1_LEN+BUFF; i++) 
     scratch[i] = 0;  // clear out the scratch
     
    for (uint8_t i = 0; i < TRACK1_LEN+BUFF; i++) {
      // for each bit starting with the MSB of the LAST 'byte' to the LSB of the first byte
      for (int8_t j=0; j < 7; j++) {
         if (track1[TRACK1_LEN+BUFF-1-i] & _BV(6-j))
           scratch[i] |= _BV(j);            
      } 
    }
    
    for (uint8_t i = 0; i < TRACK1_LEN+BUFF; i++) {
      track1[i] = scratch[i];
    }
    
    // get rid of leading zero bits and possible single bit flips
    while (((track1[0] & 0x1) == 0) || track1[1] == 0)
      shifttrack(track1, scratch, LEFT);
  }
    
  if (verifycard(track1)) {

#ifdef _SERIAL
    Serial.println("Swiped!");
    for (uint8_t i = 0; i < TRACK1_LEN; i++) {
      Serial.print(track1[i], HEX); 
      Serial.print(" "); 
    }
    Serial.println();
    for (uint8_t i = 0; i < TRACK1_LEN; i++) {
#if ARDUINO >= 100
      Serial.write((track1[i] & 0x3F)+0x20);
#else
      Serial.print((track1[i] & 0x3F)+0x20, BYTE); 
#endif
      Serial.print(" "); 
    }
    Serial.println();
    for (uint8_t i = 0; i < 6; i++) {
      for (uint8_t j = 0; j < 7; j++) {
       if (track1[i] & _BV(j)) {
         Serial.print('1');
       } else {
         Serial.print('0');
       }
      }
    }
    Serial.println();
#endif

    // FIND PAN
    uint8_t i=2;
    while ((track1[i] & 0x3F) != 0x3E) {
#if ARDUINO >= 100
 #ifdef _SERIAL
        Serial.write((track1[i] & 0x3F)+0x20);
 #endif
 #ifdef _KEYBOARD
        Keyboard.write((track1[i] & 0x3F)+0x20);
 #endif
#else
 #ifdef _SERIAL
        Serial.print((track1[i] & 0x3F)+0x20, BYTE); 
 #endif
 #ifdef _KEYBOARD
        Keyboard.print((track1[i] & 0x3F)+0x20, BYTE);
 #endif
#endif
      i++;
    }
    i++;
    char fname[26], lname[26];
    
    // LAST NAME
    uint8_t j=0;
    while ((track1[i] & 0x3F) != 0xF) {
#ifdef _SERIAL
#if ARDUINO >= 100
      Serial.write((track1[i] & 0x3F)+0x20);
#else
      Serial.print((track1[i] & 0x3F)+0x20, BYTE); 
#endif
#endif
      lname[j++] = (track1[i] & 0x3F)+0x20;
      i++;
    }
    lname[j] = 0;
    i++;
    j=0;
    // FIRST NAME
    while ((track1[i] & 0x3F) != 0x3E) {
#ifdef _SERIAL
#if ARDUINO >= 100
      Serial.write((track1[i] & 0x3F)+0x20);
#else
      Serial.print((track1[i] & 0x3F)+0x20, BYTE); 
#endif
#endif
      
      fname[j++] = (track1[i] & 0x3F)+0x20;

      i++;
    }
    fname[j] = 0;
    i++;
    char y1, y2, m1, m2;
    y1 = (track1[i++] & 0x3F)+0x20;
    y2 = (track1[i++] & 0x3F)+0x20;
    m1 = (track1[i++] & 0x3F)+0x20;
    m2 = (track1[i++] & 0x3F)+0x20;
  
#ifdef _KEYBOARD
      Keyboard.print('\t');
#if ARDUINO >= 100
      Keyboard.write(m1);
      Keyboard.write(m2);
      Keyboard.write(y1);
      Keyboard.write(y2);
#else
      Keyboard.print(m1, BYTE);
      Keyboard.print(m2, BYTE);
      Keyboard.print(y1, BYTE);
      Keyboard.print(y2, BYTE);
#endif
    
      Keyboard.print('\t'); // tab to amount
      Keyboard.print('\t'); // tab to invoice
      Keyboard.print('\t'); // tab to description
      Keyboard.print("HOPE conference kits from Adafruit.com");
      Keyboard.print('\t'); // tab to customer ID
      Keyboard.print('\t'); // tab to first name
      Keyboard.print(fname);
      Keyboard.print('\t'); // tab to last name
      Keyboard.print(lname);
      
      for (uint8_t i=0; i<5; i++) {
        Keyboard.set_modifier(MODIFIERKEY_SHIFT);
        Keyboard.set_key1(KEY_TAB);
        Keyboard.send_now();
        Keyboard.set_modifier(0);
        Keyboard.set_key1(0);
        Keyboard.send_now();
      }

#endif

    beep(PIEZO, 4000, 200);
  } else {
    beep(PIEZO, 1000, 200);
    
#ifdef _SERIAL
      Serial.println("Failed!");
      for (uint8_t i = 0; i < TRACK1_LEN; i++) {
        Serial.print(track1[i], HEX); 
        Serial.print(" "); 
      }
      Serial.println();
      for (uint8_t i = 0; i < 6; i++) {
        for (uint8_t j = 0; j < 7; j++) {
         if (track1[i] & _BV(j)) {
           Serial.print('1');
         } else {
           Serial.print('0');
         }
        }
      }
    }
    Serial.println();
#endif
  
  //Serial.println(zeros, DEC);
  
  for (uint8_t i = 0; i < TRACK1_LEN+BUFF; i++) {
    track1[i] = scratch[i] = 0;
  }
  
  while (! digitalRead(CARD2));
  return;
}

uint8_t verifycard(byte track[]) {
  uint8_t parityok = 1;
  
  // calculate parity for each byte
  for (uint8_t i = 0; i < TRACK1_LEN; i++) {
    uint8_t p = 1;
    for (uint8_t j = 0; j < 6; j++) {
      if (track1[i] & _BV(j))
        p++;
    }
    p %= 2;
    if (p != track1[i] >> 6) {
      //Serial.print("Bad parity on ");
      //Serial.println(track1[i], HEX);
      parityok = 0;
    }
    if (track1[i] == 0x1F) break;
  }
  
  if ((track1[0] == 0x45) && (track1[1] == 0x62) && parityok) {
    return 1;
  }
  return 0;
}

// We use this to s
void shifttrack(byte track[], byte shiftbuffer[], uint8_t dir) {
  if (dir == RIGHT) {
    // shift right
     uint8_t x =0;
    
    for (uint8_t i = 0; i < TRACK1_LEN+BUFF; i++) {
      shiftbuffer[i] = ((track[i] << 1) | x) & 0x3F;
      x = (track[i]>>6) & 0x1; // snag the parity bit
    } 
  } else {
    // left
    uint8_t x =0;
    
    for (uint8_t i = 0; i < TRACK1_LEN+BUFF; i++) {
      x = track[i+1] & 0x1; // snag the bit
      shiftbuffer[i] = ((track[i] >> 1) | (x << 6));

    } 
  }
  
  for (uint8_t i = 0; i < TRACK1_LEN+BUFF; i++) {
    track[i] = shiftbuffer[i];
  }
}
