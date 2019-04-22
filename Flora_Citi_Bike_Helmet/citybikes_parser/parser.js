//Change the URL to whichever city you'd like to parse.  You can then execute this file with node.js from the command line:
//node parser.js

//The results will be a multi-dimensional array that you can just plug into the bike helmet code for the city you live in!
//Make sure to also update the #define with the size of the array.  This is the last number that is output after running this parser.

var request = require('request');
var BIKE_SHARE_URL = 'http://api.citybik.es/citibikenyc.json';
request(BIKE_SHARE_URL, function (error, response, body) {
  if (!error && response.statusCode == 200) {
    var comma = ",";
    var locations = JSON.parse(body);
    locations.forEach(function(l, i) {
      if (i === locations.length-1)
        comma = "";

      console.log("  {" + (l.lat / 1000000).toFixed(6) + ", " + (l.lng / 1000000).toFixed(6) + "}" + comma);
    });

    console.log(locations.length);
  }
});
