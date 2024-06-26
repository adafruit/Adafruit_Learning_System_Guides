// SPDX-FileCopyrightText: 2019 Anne Barela for Adafruit Industries
//
// SPDX-License-Identifier: MIT

const uint8_t Z0[4] = {
  B00000000,  
  B00000000,
  B00110000,
  B00011000,
};

const uint8_t Z1[4] = {
  B00000000,  
  B00001000,
  B00011000,
  B00010000,
};

const uint8_t S0[4] = {
  B00000000,  
  B00000000,
  B00011000,
  B00110000,
};

const uint8_t S1[4] = {
  B00000000,  
  B00010000,
  B00011000,
  B00001000,
};

const uint8_t J0[4] = {
  B00000000,  
  B00000000,
  B00111000,
  B00001000,
};

const uint8_t J1[4] = {
  B00000000,  
  B00010000,
  B00010000,
  B00110000,
};

const uint8_t J2[4] = {
  B00000000,  
  B00100000,
  B00111000,
  B00000000,
};

const uint8_t J3[4] = {
  B00000000,  
  B00011000,
  B00010000,
  B00010000,
};

const uint8_t L0[4] = {
  B00000000,  
  B00000000,
  B00111000,
  B00100000,
};

const uint8_t L1[4] = {
  B00000000,  
  B00110000,
  B00010000,
  B00010000,
};

const uint8_t L2[4] = {
  B00000000,  
  B00001000,
  B00111000,
  B00000000,
};

const uint8_t L3[4] = {
  B00000000,  
  B00010000,
  B00010000,
  B00011000,
};

const uint8_t T0[4] = {
  B00000000,  
  B00000000,
  B00111000,
  B00010000,
};

const uint8_t T1[4] = {
  B00000000,  
  B00010000,
  B00110000,
  B00010000,
};

const uint8_t T2[4] = {
  B00000000,  
  B00010000,
  B00111000,
  B00000000,
};

const uint8_t T3[4] = {
  B00000000, 
  B00010000,
  B00011000,
  B00010000,
};

const uint8_t I0[4] = {
  B00000000,  
  B00000000,
  B00111100,
  B00000000,
};

const uint8_t I1[4] = {
  B00010000,  
  B00010000,
  B00010000,
  B00010000,
};

const uint8_t O0[4] = {
  B00000000,  
  B00000000,
  B00011000,
  B00011000,
};

//                                        0,  1, 2,  3, 4,  5, 6,  7, 8, 9,10, 11,12,13,14, 15,16,17,18
const uint8_t*         pieces[19]={O0, Z0,Z1, S0,S1, I0,I1, J0,J1,J2,J3, L0,L1,L2,L3, T0,T1,T2,T3};
const uint8_t*  piecesRotated[19]={O0, Z1,Z0, S1,S0, I1,I0, J1,J2,J3,J0, L1,L2,L3,L0, T1,T2,T3,T0};
const uint8_t* piecesGenerated[7]={O0, Z0, S0, I0, J0, L0, T0};
