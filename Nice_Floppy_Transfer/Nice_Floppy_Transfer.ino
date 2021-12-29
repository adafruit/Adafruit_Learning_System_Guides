#include <Adafruit_SPIDevice.h>

static const int pulseDelayTime = 6;

#define DENSITY_PIN  5     // IDC 2
// IDC 4 no connect
// IDC 6 no connect
#define INDEX_PIN    6     // IDC 8
// IDC 10 no connect
#define SELECT_PIN   A5    // IDC 12
// IDC 14 no connect
#define MOTOR_PIN    9     // IDC 16
#define DIR_PIN     10     // IDC 18
#define STEP_PIN    11     // IDC 20
#define READY_PIN   A0     // IDC 22
#define SIDE_PIN    A1     // IDC 
#define READ_PIN    12
#define PROT_PIN    A3
#define TRK0_PIN    A4

#define MAX_FLUX_PULSE_PER_TRACK (500000 / 5) // 500khz / 5 hz per track rotation
#define MAX_TRACKS 80
#define STEP_OUT HIGH
#define STEP_IN LOW

#define LED_PIN 13

BusIO_PortReg *indexPort, *dataPort, *ledPort;
BusIO_PortMask indexMask, dataMask, ledMask;

inline bool read_index(void) {
  return *indexPort & indexMask;
}
inline bool read_data(void) {
  return *dataPort & dataMask;
}

void setup() {
  Serial.begin(115200);      
  while (!Serial) delay(100);
  pinMode(LED_PIN, OUTPUT);

  // deselect drive
  pinMode(SELECT_PIN, OUTPUT);
  digitalWrite(SELECT_PIN, HIGH);
  
  // motor enable pin, drive low to turn on motor
  pinMode(MOTOR_PIN, OUTPUT);
  digitalWrite(MOTOR_PIN, HIGH);
  
  // set motor direction (low is in, high is out)
  pinMode(DIR_PIN, OUTPUT);
  digitalWrite(DIR_PIN, LOW); // move inwards to start

  // step track pin, pulse low for 3us min, 3ms max per pulse
  pinMode(STEP_PIN, OUTPUT);
  digitalWrite(STEP_PIN, HIGH);

  // side selector
  pinMode(SIDE_PIN, OUTPUT);
  digitalWrite(STEP_PIN, HIGH);  // side 0 to start

  pinMode(INDEX_PIN, INPUT_PULLUP);
  pinMode(TRK0_PIN, INPUT_PULLUP);
  pinMode(PROT_PIN, INPUT_PULLUP);
  pinMode(READY_PIN, INPUT_PULLUP);
  pinMode(READ_PIN, INPUT_PULLUP);

  indexPort = (BusIO_PortReg *)portInputRegister(digitalPinToPort(INDEX_PIN));
  indexMask = digitalPinToBitMask(INDEX_PIN);
  dataPort = (BusIO_PortReg *)portInputRegister(digitalPinToPort(READ_PIN));
  dataMask = digitalPinToBitMask(READ_PIN);
  ledPort = (BusIO_PortReg *)portOutputRegister(digitalPinToPort(LED_PIN));
  ledMask = digitalPinToBitMask(LED_PIN);
  
  Serial.println("its time for a nice floppy transfer!");

  digitalWrite(SELECT_PIN, HIGH);
  delay(100);
  // Main motor turn on
  digitalWrite(MOTOR_PIN, LOW);
  // Select drive
  digitalWrite(SELECT_PIN, LOW);
  delay(1000);

  Serial.print("Seeking track 00...");
  if (! goto_track(1)) {
    Serial.println("Failed to seek to track");
    while (1) yield();
  }
  Serial.println("done!");
}
uint32_t time_stamp = 0;

void wait_for_index_pulse_low(void) {
  // initial state
  bool index_state = read_index();
  bool last_index_state = index_state;

  // wait until last index state is H and current state is L
  while (true) {
    index_state = read_index();
    if (last_index_state && !index_state) {
      return;
    }
    last_index_state = index_state;
  }
}

void print_pulses(uint8_t *pulses, uint32_t num_pulses) {
  for (uint32_t i=0; i<num_pulses; i++) {
    Serial.print(pulses[i]);
    Serial.print(", ");
  }
  Serial.println();
}

void print_pulse_bins(uint8_t *pulses, uint32_t num_pulses) {
  // lets bin em!
  uint32_t bins[32][2];
  memset(bins, 0, 32*2*sizeof(uint32_t));

  // we'll add each pulse to a bin so we can figure out the 3 buckets
  for (uint32_t i=0; i<num_pulses; i++) {
    uint8_t p = pulses[i];
    // find a bin for this pulse
    uint8_t bin = 0;
    for (bin=0; bin<32; bin++) {
      // bin already exists? increment the count!
      if (bins[bin][0] == p) {
        bins[bin][1] ++;
        break;
      }
      if (bins[bin][0] == 0) {
        // ok we never found the bin, so lets make it this one!
        bins[bin][0] = p;
        bins[bin][1] = 1;
        break;
      }
    }
    if (bin == 32) Serial.println("oof we ran out of bins but we'll keep going");
  }
  // this is a very lazy way to print the bins sorted
  for (uint8_t pulse_w=1; pulse_w<255; pulse_w++) {
    for (uint8_t b=0; b<32; b++) {
      if (bins[b][0] == pulse_w) {
        Serial.print(bins[b][0]);
        Serial.print(": ");
        Serial.println(bins[b][1]);
      }
    }
  }
}

void capture_track(void) {
  uint8_t pulse_count;
  uint8_t pulses[MAX_FLUX_PULSE_PER_TRACK];
  uint8_t *pulses_ptr = pulses;
  
  memset(pulses, 0, MAX_FLUX_PULSE_PER_TRACK); // zero zem out

  noInterrupts();
  wait_for_index_pulse_low();

  // ok we have a h-to-l transition so...
  bool last_index_state = read_index();
  while (true) {
    bool index_state = read_index();
    // ahh another H to L transition, we're done with this track!
    if (last_index_state && !index_state) {
      break;
    }
    last_index_state = index_state;

    // muahaha, now we can read track data!
    pulse_count = 0;
    // while pulse is in the low pulse, count up
    while (!read_data()) pulse_count++;
    *ledPort |= ledMask;

    // while pulse is high, keep counting up
    while (read_data()) pulse_count++;
    *ledPort &= ~ledMask;
    
    pulses_ptr[0] = pulse_count;
    pulses_ptr++; 
  }
  // whew done
  interrupts();

  int32_t num_pulses = pulses_ptr - pulses;
  Serial.print("Captured ");
  Serial.print(num_pulses);
  Serial.println(" flux transitions");

  //print_pulses(pulses, num_pulses);
  //print_pulse_bins(pulses, num_pulses);
}

void loop() {
  capture_track();
 
  if ((millis() - time_stamp) > 1000) {
    Serial.print("Ready? ");
    Serial.println(digitalRead(READY_PIN) ? "No" : "Yes");
    Serial.print("Write Protected? "); 
    Serial.println(digitalRead(PROT_PIN) ? "No" : "Yes");
    Serial.print("Track 0? ");
    Serial.println(digitalRead(TRK0_PIN) ? "No" : "Yes");
    time_stamp = millis();
  }
}



void step(bool dir, uint8_t times) {
  digitalWrite(DIR_PIN, dir);
  delayMicroseconds(10); // 1 microsecond, but we're generous
  
  while (times--) {
    digitalWrite(STEP_PIN, HIGH);
    delay(3); // 3ms min per step
    digitalWrite(STEP_PIN, LOW);
    delay(3); // 3ms min per step
    digitalWrite(STEP_PIN, HIGH); // end high
  }
}

bool goto_track(uint8_t track_num) {
  // track 0 is a very special case because its the only one we actually know we got to
  if (track_num == 0) {
    uint8_t max_steps = MAX_TRACKS;
    while (max_steps--) {
      if (!digitalRead(TRK0_PIN)) 
        return true;
      step(STEP_OUT, 1);
    }
    return false; // we 'timed' out!
  }
  if (!goto_track(0)) return false;
  step(STEP_IN, max(track_num, MAX_TRACKS-1));
  return true;
}
