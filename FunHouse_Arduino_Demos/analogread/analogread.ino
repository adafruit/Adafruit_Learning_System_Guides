void setup() {
  Serial.begin(115200);
}
void loop() {
  // put your main code here, to run repeatedly:
  uint32_t vol;
  vol = ((analogRead(17) * 30 ) / 8191);
  Serial.printf("17 : %d\n", vol);
  vol = ((analogRead(1) * 30 ) / 8191);
  Serial.printf("1 : %d\n", vol);
  delay(1000);
}
