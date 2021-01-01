{
  "boopThreshold"   : 17500, // lower is more sensitive
  "eyeRadius"       : 125, // radius, in pixels
  "irisRadius"      : 120,  // radius, in pixels
  "slitPupilRadius" : 0, // height, in pixels; 0 is round pupil

  "irisTexture"     : "eagle/iris.bmp",
//  "scleraTexture"   : "eagle/sclera.bmp",
  "scleraColor"     : [ 64, 24, 22 ],
  "pupilColor"      : [ 0, 0, 0 ],
  "backColor"       : [ 140, 40, 20 ], // covers the outermost/backmost part of the eye where the sclera texture map (or color) doesn’t reach
  "eyelidIndex"     : "0x00", // 8-bit value; from table learn.adafruit.com/assets/61921

  // independent irisTexture, scleraTexture, irisColor, scleraColor,
  // pupilColor, backColor, irisAngle, scleraAngle, irisSpin, scleraSpin,
  // irisMirror, scleraMirror, and rotate can be specified
  "left" : {
  },
  "right" : {
  },

  "upperEyelid"     : "eagle/upper.bmp",
  "lowerEyelid"     : "eagle/lower.bmp",
  "tracking"        : true,
  "squint"          : 0.5, // offsets eyelid center point vertically

  "lightSensor"     : 102, // light sensor pin; 102 is MONSTER M4SK, 21 is HalloWing M4
  "pupilMin"        : 0.05, // smallest pupil size as a fraction of iris size; from 0.0 to 1.0
  "pupilMax"        : 0.3, // largest pupil size as a fraction of iris size; from 0.0 to 1.0

  "voice"           : false,
  "pitch"           : 1.0,
  "gain"            : 1.0, // microphone gain (sensitivity)
//  "waveform"        : "sine" // "square", "sine", "tri" and "saw" are supported
//  "modulate"        : 30 // waveform modulation, in Hz

  "wiichuck" : {
    "min"           : 28,
	"max"           : 229
  }
}
