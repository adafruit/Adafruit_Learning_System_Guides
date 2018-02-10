# Set any env vars needed to build

rm secrets.h
echo "#define WIFI_PASS   \"$WIFI_PASSWORD\"" >> secrets.h
echo "#define WIFI_SSID   \"$WIFI_SSID\"" >> secrets.h
echo "#define HUE_USER    \"$HUE_USER\"" >> secrets.h
echo "#define DARKSKY_KEY \"$DARKSKY_KEY\"" >> secrets.h
echo "#define AIO_USER    \"$AIO_USER\"" >> secrets.h
echo "#define AIO_KEY     \"$AIO_KEY\"" >> secrets.h
echo "" >> secrets.h

