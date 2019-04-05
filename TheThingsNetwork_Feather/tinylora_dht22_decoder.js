// TinyLoRa - DHT22 Decoder
function Decoder(bytes, port) {
  var decoded = {};

  // Decode bytes to int
  var celciusInt = (bytes[0] << 8) | bytes[1];
  var humidInt = (bytes[2] << 8) | bytes[3];
  
  // Decode int to float
  decoded.celcius = celciusInt / 100;
  decoded.humid = humidInt / 100;

  return decoded;
}