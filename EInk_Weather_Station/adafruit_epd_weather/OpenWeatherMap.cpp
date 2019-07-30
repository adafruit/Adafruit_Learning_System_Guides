#include "OpenWeatherMap.h"

String AirliftOpenWeatherMap::buildUrlCurrent(String appId, String location) {
  String units = OWM_METRIC ? "metric" : "imperial";
  return "http://api.openweathermap.org/data/2.5/weather?q=" + location + "&appid=" + appId + "&units=" + units + "&lang=" + String(OWM_LANGUAGE);
}

String AirliftOpenWeatherMap::buildUrlForecast(String appId, String location) {
  String units = OWM_METRIC ? "metric" : "imperial";
  return "http://api.openweathermap.org/data/2.5/forecast?q=" + location + "&cnt=6&appid=" + appId + "&units=" + units + "&lang=" + String(OWM_LANGUAGE);
}

String AirliftOpenWeatherMap::getMeteoconIcon(String icon) {
  // clear sky
  // 01d
  if (icon == "01d") 	{
    return "B";
  }
  // 01n
  if (icon == "01n") 	{
    return "C";
  }
  // few clouds
  // 02d
  if (icon == "02d") 	{
    return "H";
  }
  // 02n
  if (icon == "02n") 	{
    return "4";
  }
  // scattered clouds
  // 03d
  if (icon == "03d") 	{
    return "N";
  }
  // 03n
  if (icon == "03n") 	{
    return "5";
  }
  // broken clouds
  // 04d
  if (icon == "04d") 	{
    return "Y";
  }
  // 04n
  if (icon == "04n") 	{
    return "%";
  }
  // shower rain
  // 09d
  if (icon == "09d") 	{
    return "R";
  }
  // 09n
  if (icon == "09n") 	{
    return "8";
  }
  // rain
  // 10d
  if (icon == "10d") 	{
    return "Q";
  }
  // 10n
  if (icon == "10n") 	{
    return "7";
  }
  // thunderstorm
  // 11d
  if (icon == "11d") 	{
    return "P";
  }
  // 11n
  if (icon == "11n") 	{
    return "6";
  }
  // snow
  // 13d
  if (icon == "13d") 	{
    return "W";
  }
  // 13n
  if (icon == "13n") 	{
    return "#";
  }
  // mist
  // 50d
  if (icon == "50d") 	{
    return "M";
  }
  // 50n
  if (icon == "50n") 	{
    return "M";
  }
  // Nothing matched: N/A
  return ")";

}

bool AirliftOpenWeatherMap::updateCurrent(OpenWeatherMapCurrentData &data, String json)
{
  Serial->println("updateCurrent()");
  DynamicJsonDocument doc(2000);
  //StaticJsonDocument<2000> doc;

  DeserializationError error = deserializeJson(doc, json);
  if (error) {
    Serial->println(String("deserializeJson() failed: ") + (const char *)error.c_str());
    Serial->println(json);
    setError(String("deserializeJson() failed: ") + error.c_str());
    return false;
  }

  int code = (int) doc["cod"];
  if(code != 200)
  {
    Serial->println(String("OpenWeatherMap error: ") + (const char *)doc["message"]);
    setError(String("OpenWeatherMap error: ") + (const char *)doc["message"]);
    return false;
  }
  
  data.lat = (float) doc["coord"]["lat"];
  data.lon = (float) doc["coord"]["lon"];
  
  data.main = (const char*) doc["weather"][0]["main"];  
  data.description = (const char*) doc["weather"][0]["description"];
  data.icon = (const char*) doc["weather"][0]["icon"];
  
  data.cityName = (const char*) doc["name"];
  data.visibility = (uint16_t) doc["visibility"];
  data.timezone = (time_t) doc["timezone"];
  
  data.country = (const char*) doc["sys"]["country"];
  data.observationTime = (time_t) doc["dt"];
  data.sunrise = (time_t) doc["sys"]["sunrise"];
  data.sunset = (time_t) doc["sys"]["sunset"];
  
  data.temp = (float) doc["main"]["temp"];
  data.pressure = (uint16_t) doc["main"]["pressure"];
  data.humidity = (uint8_t) doc["main"]["humidity"];
  data.tempMin = (float) doc["main"]["temp_min"];
  data.tempMax = (float) doc["main"]["temp_max"];

  data.windSpeed = (float) doc["wind"]["speed"];
  data.windDeg = (float) doc["wind"]["deg"];
  return true;
}

bool AirliftOpenWeatherMap::updateForecast(OpenWeatherMapForecastData &data, String json, int day)
{
  Serial->println("updateForecast()");
  DynamicJsonDocument doc(5000);
  //StaticJsonDocument<5000> doc;

  DeserializationError error = deserializeJson(doc, json);
  if (error) {
    Serial->println(String("deserializeJson() failed: ") + (const char *)error.c_str());
    Serial->println(json);
    setError(String("deserializeJson() failed: ") + error.c_str());
    return false;
  }

  int code = (int) doc["cod"];
  if(code != 200)
  {
    Serial->println(String("OpenWeatherMap error: ") + (const char *)doc["message"]);
    setError(String("OpenWeatherMap error: ") + (const char *)doc["message"]);
    return false;
  }

  data.observationTime = (time_t) doc["list"][day]["dt"];

  data.temp = (float) doc["list"][day]["main"]["temp"];
  data.pressure = (uint16_t) doc["list"][day]["main"]["pressure"];
  data.humidity = (uint8_t) doc["list"][day]["main"]["humidity"];
  data.tempMin = (float) doc["list"][day]["main"]["temp_min"];
  data.tempMax = (float) doc["list"][day]["main"]["temp_max"];

  data.main = (const char*) doc["list"][day]["weather"][0]["main"];  
  data.description = (const char*) doc["list"][day]["weather"][0]["description"];
  data.icon = (const char*) doc["list"][day]["weather"][0]["icon"];
  return true;
}
