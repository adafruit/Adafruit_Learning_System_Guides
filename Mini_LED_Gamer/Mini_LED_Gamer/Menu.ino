const uint8_t tetrisBoot[16]={
  B00000000,
  B00000000,
  B00001000,
  B00001100,
  B00000100,
  B00000000,
  B00000000,
  B00100000,
  B11100000,
  B11111010,
  B10111110,
  B11011110,
  B01111111,
  B11111101,
  B11011111,
  B10110111
};

const uint8_t snakeBoot[16]={
  B00000000,
  B00000000,
  B00000100,
  B00000000,
  B00000000,
  B00000000,
  B00000100,
  B00000100,
  B00000100,
  B01111100,
  B01000000,
  B01000000,
  B01100000,
  B00100000,
  B00100000,
  B00100000
};

const uint8_t paintBoot[16]={
  B01100000,
  B11000000,
  B10000010,
  B00001010,
  B00011110,
  B00110110,
  B01100011,
  B11000001,
  B01010101,
  B01010001,
  B01111111,
  B00101000,
  B11101111,
  B00000000,
  B11011011,
  B00000000
};

uint8_t option=1;

void changeMode(){
  mode = option;
}

uint8_t* getMenu(){
  switch(option) {
    case 1:
      return (uint8_t*)tetrisBoot;
    case 2:
      return (uint8_t*)snakeBoot;
    case 3:
      return (uint8_t*)paintBoot;
  }
  return 0;
}

void changeOption(int8_t i){
  int8_t temp = option+i;
  if (temp<1 || temp>3) return;
  option=temp;
}
