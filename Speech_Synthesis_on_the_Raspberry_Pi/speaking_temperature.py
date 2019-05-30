import os

# Loop reading measurements every minute.
print 'Press Ctrl-C to quit.'
while True:
    temp = sensor.readTempC()
    os.system("flite -t 'The temperature is " + temp + " degrees'" &)
    time.sleep(60.0)
