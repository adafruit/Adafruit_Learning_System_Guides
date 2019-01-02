// TinyLoRa - Raspberry Pi CPU Load Decoder
function Decoder(bytes, port) {
  var decoded = {};

  // Decode bytes to int
  var CPU_Load = (bytes[0] << 8) | bytes[1];

  // Decode int to float
  decoded.CPU_Load = CPU_Load / 100;

  return decoded;
}