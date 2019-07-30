// VCNL4010 code adapted from:
//   https://github.com/adafruit/Adafruit_VCNL4010
#ifndef ADAFRUIT_VCNL4010_H
#define ADAFRUIT_VCNL4010_H

// the i2c address
#define VCNL4010_I2CADDR_DEFAULT 0x13

// commands and constants
#define VCNL4010_COMMAND 0x80
#define VCNL4010_PRODUCTID 0x81
#define VCNL4010_PROXRATE 0x82
#define VCNL4010_IRLED 0x83
#define VCNL4010_AMBIENTPARAMETER 0x84
#define VCNL4010_AMBIENTDATA 0x85
#define VCNL4010_PROXIMITYDATA 0x87
#define VCNL4010_INTCONTROL 0x89
#define VCNL4010_PROXINITYADJUST 0x8A
#define VCNL4010_INTSTAT 0x8E
#define VCNL4010_MODTIMING 0x8F

typedef enum
  {
    VCNL4010_3M125   = 3,
    VCNL4010_1M5625  = 2,
    VCNL4010_781K25  = 1,
    VCNL4010_390K625 = 0,
  } vcnl4010_freq;

#define VCNL4010_MEASUREAMBIENT 0x10
#define VCNL4010_MEASUREPROXIMITY 0x08
#define VCNL4010_AMBIENTREADY 0x40
#define VCNL4010_PROXIMITYREADY 0x20

class Adafruit_VCNL4010 {
public:
  Adafruit_VCNL4010() {}

  bool begin(uint8_t a = VCNL4010_I2CADDR_DEFAULT);
  uint16_t readProximity();
  
private:
  uint8_t read8(uint8_t address);
  uint16_t read16(uint8_t address);
  void write8(uint8_t address, uint8_t data);
  uint8_t _i2caddr;
  
};

#endif
