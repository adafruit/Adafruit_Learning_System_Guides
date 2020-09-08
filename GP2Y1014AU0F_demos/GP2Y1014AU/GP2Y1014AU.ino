#define dustPin A0 // Black wire
#define ledPin 5  // White wire

#define ANALOG_VOLTAGE 3.3 // analog top of range

// Yellow, Green wire connects to ground
// Blue wire connects to 5V via 150 ohm resistor (see DS)
// Red wire connects to 5V
 
void setup()
{
  Serial.begin(115200);
  while (!Serial) delay(100);
  
  Serial.println("GP2Y1010AU0F Sensor demo");
  pinMode(ledPin, OUTPUT);
}
 
 
void loop()
{
  float output_voltage, dust_density;
  
  digitalWrite(ledPin, LOW); // power on the LED
  delayMicroseconds(280); // Wait 0.28ms according to DS
  // take analog reading
  output_voltage = analogRead(dustPin); 
  delay(1);
  
  digitalWrite(ledPin, HIGH); // turn the LED off

  output_voltage = (output_voltage / 1023) * ANALOG_VOLTAGE;
  dust_density = (0.18 * output_voltage) - 0.1;

  Serial.print("Voltage = ");
  Serial.print(output_voltage);
  Serial.print(",\tDust Density = ");
  Serial.print(dust_density);
  Serial.println(" mg/m3");
  delay(1000);
}
