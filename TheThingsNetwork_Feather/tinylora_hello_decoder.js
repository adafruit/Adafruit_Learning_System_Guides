// TTN Decoder for 'Hello LoRa'
function Decoder(bytes, port) {
  // Decode plain text; for testing only 
  return {
      myTestValue: String.fromCharCode.apply(null, bytes)
  };
}