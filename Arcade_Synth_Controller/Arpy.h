/**
 * Arpy - a class to do arpeggios for you
 * 12 Jan 2022 - Tod Kurt @todbot
 * See https://github.com/todbot/mozzi_experiments/ for examples
 */
class Arpy 
{
  public:
  
  Arpy(): enabled(false), arp_id(0), arp_pos(0), root_note(0), note_played(0)
  {
    tr_steps = 1; tr_dist = 12;  tr_pos = 0; // FIXME make these defaults
  }

  // turn Arpy on or off
  void on() { enabled = true; }
  void off() {
      enabled = false;
      if( noteOffHandler) { noteOffHandler( note_played ); }
  }
  // let you know what Arpy thinks about doing its job
  bool isOn() { return enabled; }

  // pick which arpeggio to play
  void setArpId(uint8_t arp_id) { arp_id = arp_id % arp_count; }

  // which arpeggio is currently set
  uint8_t getArpId() { return arp_id; }

  // go to next arpeggio, a little convenience function
  void nextArpId() {  arp_id = (arp_id+1) % arp_count; }

  // return acount of how many different arpeggios Arpy knows
  uint8_t getArpCount() { return arp_count; }

  // set the root note of the arpeggio
  void setRootNote( uint8_t note ) { root_note = note; }
  uint8_t getRootNote() { return root_note; }

  // set the octave offset for root_note (root_note += (octave_offset*12)
  void setOctaveOffset( uint8_t offset ) { octave_offset = offset; }
  uint8_t getOctaveOffset() { return octave_offset; }

  // set BPM of arpeggio
  void setBPM( float bpm ) {
    bpm = bpm;
    per_beat_millis = 1000 * 60 / bpm;
    note_duration = gate_percentage * per_beat_millis;
  }

  // set note duration as a percentage of BPM
  void setGateTime( float percentage ) {
    if( percentage < 0 || percentage > 1 ) { return; }
    gate_percentage = percentage;
  }
  float getGateTime() { return gate_percentage; } // percentage 0.0 - 1.0

  // set the function to call when note on happens
  void setNoteOnHandler(void (*anoteOnHandler)(uint8_t)) {
    noteOnHandler = anoteOnHandler;
  }

  // set the function to call when note off happens
  void setNoteOffHandler(void (*anoteOffHandler)(uint8_t)) {
    noteOffHandler = anoteOffHandler;
  }

  // number of "octaves" (if transpose distance=12)
  void setTransposeSteps(uint8_t steps) {  if( steps > 0) { tr_steps = steps; } }

  // the distance in semitones between steps, often 12 for an octave
  void setTransposeDistance(uint8_t dist) {  tr_dist = dist; }

  // call update as fast as possible, will trigger noteOn and noteOff functions
  void update() { update(-1); } // -1 means "root note is updated immediately when changed"

  // call update as fast as possible, will trigger noteOn and noteOff function
  // "root_note_new" is new root note to use at top of arp "measure"
  // negative notes are invalid. "root_note_new == -1" is used as internal signaling
  void update(int root_note_new)
  {
    if( !enabled ) { return; }

    uint32_t now = millis();

    if( now - last_beat_millis > per_beat_millis )  {
      last_beat_millis = now;
      int8_t tr_amount = tr_dist * tr_pos;  // tr_pos may be zero
      
      // only make musical changes at start of a new measure // FIXME allow immediate
      if( arp_pos == 0 ) {
        if( root_note_new >= 0 ) { root_note = root_note_new; }
        tr_pos = (tr_pos + 1) % tr_steps;
      }
      note_played = root_note + arps[arp_id][arp_pos] + tr_amount;
      note_played = constrain(note_played + (12 * octave_offset), 0,127);
      if( noteOnHandler) { noteOnHandler( note_played ); }
      arp_pos = (arp_pos+1) % arp_len;
    }
  
    if( now - last_beat_millis > note_duration ) { 
      if( note_played != 0 ) { // we have a note to turn off!
        if( noteOffHandler) { noteOffHandler( note_played ); }
        note_played = 0;  // say we've turned off the note
      }
    }
  }

  private:
    bool    enabled;       // is arp playing or not
    float   bpm;           // our arps per minute
    uint8_t arp_id;        // which arp we using
    uint8_t arp_pos;       // where in current arp are we
    uint8_t tr_steps;      // if transposing, how many times, 1= normal
    int8_t  tr_dist;       // like an octave
    uint8_t tr_pos;        // which tranposed we're on (0..tr_steps)
    uint8_t root_note;     //
    uint8_t octave_offset; // offset for root_note
    uint16_t per_beat_millis; // = 1000 * 60 / bpm;

    uint8_t note_played;    // the note we have played, so we can unplay it later
    uint16_t note_duration;
    float gate_percentage;  // percentage of per_beat_millis to play a note, 0.0-1.0

    uint32_t last_beat_millis;

    void (*noteOnHandler)(uint8_t) = nullptr;
    void (*noteOffHandler)(uint8_t) = nullptr;

    static const int arp_len = 4;  // number of notes in an arp
    static const uint8_t arp_count= 8;   // how many arps in "arps"
    int8_t arps[arp_count][arp_len] = {
      {0, 4, 7, 12},    // major
      {0, 3, 7, 10},    // minor 7th
      {0, 3, 6, 3},     // Diminished
      {0, 5, 7, 12},    // Suspended 4th
      {0, 12, 0, -12},  // octaves
      {0, 12, 24, -12}, // octaves 2
      {0, -12, -12, 0}, // octaves 3 (bass)
      {0, 0, 0, 0},     // root
    };

    // FIXME: how to programmatically set arps?

};
