{
  // This is a comment
  "eyeRadius"      : 125,
  "eyelidIndex"    : "0x00", // From table: learn.adafruit.com/assets/61921
  "irisRadius"     : 125,    // Iris = whole eye!
  "pupilMin"       : 0,      // Pupil is always 0 size
  "pupilMax"       : 0,
  "pupilColor"     : [ 255, 255, 169 ], // Shouldn't show, but just in case
  "scleraColor"    : [ 255, 0, 0 ],
  "backColor"      : [ 255, 0, 0 ],
  "irisTexture"    : "doom-spiral/spiral.bmp",
  // The doom-red and doom-spiral eyelid bitmaps don't fully close.
  // This is to give the IMPRESSION of a blink without actually blinking,
  // so human eye behind is hidden better when doing Pepper's ghost trick.
  "upperEyelid"    : "doom-spiral/upper.bmp",
  "lowerEyelid"    : "doom-spiral/lower.bmp",
  "left" : {
    "irisSpin"     : 80    // Rotate iris @ 80 RPM
  },
  "right" : {
    "irisMirror"   : true, // Flip spiral image
    "irisSpin"     : 70    // Slightly different speed for weirdness
  }
}
