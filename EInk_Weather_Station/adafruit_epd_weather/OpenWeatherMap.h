#pragma once
#include "secrets.h"
#include <ArduinoJson.h>          //https://github.com/bblanchon/ArduinoJson

typedef struct OpenWeatherMapCurrentData {
  // "lon": 8.54,
  float lon;
  // "lat": 47.37
  float lat;
  // "id": 521,
  uint16_t weatherId;
  // "main": "Rain",
  String main;
  // "description": "shower rain",
  String description;
  // "icon": "09d"
  String icon;
  String iconMeteoCon;
  // "temp": 290.56,
  float temp;
  // "pressure": 1013,
  uint16_t pressure;
  // "humidity": 87,
  uint8_t humidity;
  // "temp_min": 289.15,
  float tempMin;
  // "temp_max": 292.15
  float tempMax;
  // visibility: 10000,
  uint16_t visibility;
  // "wind": {"speed": 1.5},
  float windSpeed;
  // "wind": {deg: 226.505},
  float windDeg;
  // "clouds": {"all": 90},
  uint8_t clouds;
  // "dt": 1527015000,
  time_t observationTime;
  // "country": "CH",
  String country;
  // "sunrise": 1526960448,
  time_t sunrise;
  // "sunset": 1527015901
  time_t sunset;
  // "name": "Zurich",
  String cityName;
  time_t timezone;
} OpenWeatherMapCurrentData;

typedef struct OpenWeatherMapForecastData {
  // {"dt":1527066000,
  time_t observationTime;
  // "main":{
  //   "temp":17.35,
  float temp;
  //   "temp_min":16.89,
  float tempMin;
  //   "temp_max":17.35,
  float tempMax;
  //   "pressure":970.8,
  float pressure;
  //   "sea_level":1030.62,
  float pressureSeaLevel;
  //   "grnd_level":970.8,
  float pressureGroundLevel;
  //   "humidity":97,
  uint8_t humidity;
  //   "temp_kf":0.46
  // },"weather":[{
  //   "id":802,
  uint16_t weatherId;
  //   "main":"Clouds",
  String main;
  //   "description":"scattered clouds",
  String description;
  //   "icon":"03d"
  String icon;
  String iconMeteoCon;
  // }],"clouds":{"all":44},
  uint8_t clouds;
  // "wind":{
  //   "speed":1.77,
  float windSpeed;
  //   "deg":207.501
  float windDeg;
  // rain: {3h: 0.055},
  float rain;
  // },"sys":{"pod":"d"}
  // dt_txt: "2018-05-23 09:00:00"
  String observationTimeText;

} OpenWeatherMapForecastData;

class AirliftOpenWeatherMap{
  private:
    Stream *Serial;
    String currentKey;
    String currentParent;
    //OpenWeatherMapCurrentData *data;
    uint8_t weatherItemCounter = 0;
    bool metric = true;
    String language;
    String _error;

  public:
    AirliftOpenWeatherMap(Stream *serial){Serial = serial;};
    String buildUrlCurrent(String appId, String locationParameter);
    String buildUrlForecast(String appId, String locationParameter);
    bool updateCurrent(OpenWeatherMapCurrentData &data,String json);
    bool updateForecast(OpenWeatherMapForecastData &data,String json, int day = 0);

    void setMetric(bool metric) {this->metric = metric;}
    bool isMetric() { return metric; }
    void setLanguage(String language) { this->language = language; }
    String getLanguage() { return language; }
    void setError(String error){_error = error;}
    String getError(){return _error;}

    String getMeteoconIcon(String icon);

};
