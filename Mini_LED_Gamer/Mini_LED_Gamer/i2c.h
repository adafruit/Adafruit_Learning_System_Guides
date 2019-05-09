// This library provides the high-level functions needed to use the I2C
// serial interface supported by the hardware of several AVR processors.
#ifndef i2c_h
#define i2c_h

#include <avr/io.h>

// TWSR values (status codes)
// Master
#define TW_START				0x08
#define TW_REP_START				0x10
// Master Transmitter
#define TW_MT_SLA_ACK				0x18
#define TW_MT_SLA_NACK				0x20
#define TW_MT_DATA_ACK				0x28
#define TW_MT_DATA_NACK				0x30
#define TW_MT_ARB_LOST				0x38
// Master Receiver
#define TW_MR_ARB_LOST				0x38
#define TW_MR_SLA_ACK				0x40
#define TW_MR_SLA_NACK				0x48
#define TW_MR_DATA_ACK				0x50
#define TW_MR_DATA_NACK				0x58
// Slave Transmitter
#define TW_ST_SLA_ACK				0xA8
#define TW_ST_ARB_LOST_SLA_ACK		        0xB0
#define TW_ST_DATA_ACK				0xB8
#define TW_ST_DATA_NACK				0xC0
#define TW_ST_LAST_DATA				0xC8
// Slave Receiver
#define TW_SR_SLA_ACK				0x60
#define TW_SR_ARB_LOST_SLA_ACK		        0x68
#define TW_SR_GCALL_ACK				0x70
#define TW_SR_ARB_LOST_GCALL_ACK	        0x78
#define TW_SR_DATA_ACK				0x80
#define TW_SR_DATA_NACK				0x88
#define TW_SR_GCALL_DATA_ACK		        0x90
#define TW_SR_GCALL_DATA_NACK		        0x98
#define TW_SR_STOP			        0xA0
// Misc
#define TW_NO_INFO				0xF8
#define TW_BUS_ERROR				0x00

// defines and constants
#define TWCR_CMD_MASK		0x0F
#define TWSR_STATUS_MASK	0xF8

// return values
#define I2C_OK			0x00
#define I2C_ERROR_NODEV		0x01

//! Initialize I2C (TWI) interface
void i2cInit(void);
// Low-level I2C transaction commands 
//! Send an I2C start condition in Master mode
void i2cSendStart(void);
//! Send an I2C stop condition in Master mode
void i2cSendStop(void);
//! Wait for current I2C operation to complete
void i2cWaitForComplete(void);
//! Send an (address|R/W) combination or a data byte over I2C
void i2cSendByte(unsigned char data);
//! Receive a data byte over I2C  
// ackFlag = -1 if recevied data should be ACK'ed
// ackFlag = 0 if recevied data should be NACK'ed
void i2cReceiveByte(unsigned char ackFlag);
//! Pick up the data that was received with i2cReceiveByte()
unsigned char i2cGetReceivedByte(void);
//! Get current I2c bus status from TWSR
unsigned char i2cGetStatus(void);
void delay_10us(uint16_t x);

/*********************
 ****I2C Functions****
 *********************/

void i2cInit(void){
  // set SCL freq = F_CPU/(16+2*TWBR*4^TWPS))=16*10^6/(16+2*12)=400kHz
  TWSR &= ~(_BV(TWPS0)|_BV(TWPS1));  // clear TWPS in TWSR register, setting prescaler(TWPS) = 0
  TWBR = 12;  // set bit rate register (12 -> 400kHz; 32 -> 200kHz)
  TWCR |= _BV(TWEN);  // Enable TWI	
}

void i2cSendStart(void){
  // send start condition
  TWCR = _BV(TWINT)|_BV(TWSTA)|_BV(TWEN);
}

void i2cSendStop(void){
  // transmit stop condition
  TWCR = _BV(TWINT)|_BV(TWEN)|_BV(TWSTO);
}

void i2cWaitForComplete(void){
  // wait for i2c interface to complete operation, use i for timeout
  uint8_t i = 0;
  while ((!(TWCR & (1<<TWINT))) && (i < 90))
    i++;
}

void i2cSendByte(uint8_t data){
  delay_10us(1);
  TWDR = data;  // save data to the TWDR
  TWCR = (1<<TWINT) | (1<<TWEN);  // begin send
}

void i2cReceiveByte(uint8_t ackFlag){
  if( ackFlag ){
    // ackFlag = 1: ACK the recevied data (would like to receive more data)
    TWCR = (TWCR&TWCR_CMD_MASK)|_BV(TWINT)|_BV(TWEA);
  }
  else{
    // ackFlag = 0: NACK the recevied data (want to stop receiving data)
    TWCR = (TWCR&TWCR_CMD_MASK)|_BV(TWINT);
  }
}

unsigned char i2cGetReceivedByte(void) {
  // retieve received data byte from i2c TWDR
  return(TWDR);
}

unsigned char i2cGetStatus(void){
  // retieve current i2c status from i2c TWSR
  return(TWSR);
}

void delay_10us(uint16_t x){
  for (; x > 0 ; x--){
    for (uint8_t y = 0 ; y < 25; y++){
        asm volatile ("nop");
    }
  }
}

/*********************
 ****I2C High Level Functions****
 *********************/
 
void writeRegister(uint8_t address, uint8_t data){
  i2cSendStart();
  i2cWaitForComplete();
  i2cSendByte((address<<1));
  i2cWaitForComplete();
  i2cSendByte(data);
  i2cWaitForComplete();
  i2cSendStop();
}

void writeRegisters(uint8_t address, uint8_t regsiter, uint8_t i, uint16_t *data){
  i2cSendStart();
  i2cWaitForComplete();
  i2cSendByte((address<<1));
  i2cWaitForComplete();
  i2cSendByte(regsiter);
  i2cWaitForComplete();
  
  for (uint8_t j=0;j<i;j++) {
    i2cSendByte(data[j]&255);
    i2cWaitForComplete();
    i2cSendByte((data[j]>>8)&255);
    i2cWaitForComplete();
  }  
  i2cSendStop();
}

uint8_t readRegister(uint8_t address, uint8_t regsiter){
  i2cSendStart();
  i2cWaitForComplete();
  i2cSendByte((address<<1));
  i2cWaitForComplete();
  i2cSendByte(regsiter);
  i2cWaitForComplete();

  i2cSendStart();
  i2cWaitForComplete();
  i2cSendByte((address<<1)|0x01);
  i2cWaitForComplete();
  i2cReceiveByte(0);
  i2cWaitForComplete();
  uint8_t data = i2cGetReceivedByte();
  i2cSendStop();

  return data;
}

#endif
