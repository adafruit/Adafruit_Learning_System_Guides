// ConvertBMPinspector01 - Read and enlarge a modified 32x24 24-bit gray BMP file,
//                         display an upscaled 256x192 BMP image in 256 colors.
// Ver. 1 - Fetch filenames and display BMPs in sequence.
//          Add nav buttons and mouseover pixel temperatures
//          This sketch does no checking for file compatibility.
//          Only frm_____.bmp images from the thermal camera sketch will work.
//          Any other files in the data folder will fail.

import java.util.Date;

byte b[], colorPal[];     // Buffers for input file bytes and for colors

int i, fileCount = 0, BGcolor = 48, colorMap = 1,
    butnsX = 30, butnsY = 290,
    offsetX = 153, offsetY = 6,    // These value pairs control where the onscreen features appear
    numbersX = 40, numbersY = 48,
    probeX = 190, probeY = 210;
boolean celsiusFlag = false;
float fixedPoint[];
String[] filenames;

void setup() {

  size(480, 360);      // Size must be the first statement
  background(BGcolor); // Clear the screen with a gray background

  colorPal = new byte[1024];   // Prepare a 1K color table
  loadColorTable(colorMap, 0); // Load color table, 1 == ironbow palette
  fixedPoint = new float[5];   // A buffer for appended fixed point values

  String path = sketchPath() + "/data";  // Read from the "/data" subdirectory

  filenames = listFileNames(path);
  fileCount = filenames.length;

  i = 0;
  if(fileCount < 1) {
    println("No files found.  Stopping.");
    noLoop();
  } else {
    loadBMPscreen(i);  // Read in the first frame for inspection
  }
}

void draw() {
  int sampleX, sampleY, pixelVal;
  float sampleTemp;

  sampleX = (mouseX - offsetX) >> 3;       // Map mouse position to BMP pixel space
  sampleY = 23 - ((mouseY - offsetY) >> 3);

  noStroke();
  smooth();
  fill(BGcolor + 16);
  rect(probeX, probeY, 180, 40);   // Clear the interactive window space

  if((sampleX >= 0) && (sampleX < 32) && (sampleY >= 0) && (sampleY < 24)) { // Mouse within BMP image bounds?
    pixelVal = b[54 + (32 * sampleY + sampleX) * 3] & 0xff;                  // Read the 8-bit pixel value

    fill(colorPal[4 * pixelVal + 2] & 0xFF, colorPal[4 * pixelVal + 1] & 0xFF, colorPal[4 * pixelVal + 0] & 0xFF);
    rect(probeX, probeY, 180, 40);
    fill(BGcolor);
    rect(probeX + 10, probeY + 10, 160, 20);   // Draw a colorized frame for the interactive temp readout

    sampleTemp = (float(pixelVal) + 1.0) / 257.0 * (fixedPoint[3] - fixedPoint[1]) + fixedPoint[1];
    if(!celsiusFlag)
      sampleTemp = sampleTemp * 1.8 + 32.0;

    fill(255);       // Ready to display white interactive text
    textSize(11);
    text(sampleX, probeX + 154, probeY + 19);   // Display X Y position
    text(sampleY, probeX + 154, probeY + 29);
    textSize(15);
    text(sampleTemp, probeX + 60, probeY + 25); // Display temperature

    if(pixelVal ==   0 && fixedPoint[0] < fixedPoint[1]) // Pixel values clipped at bottom limit?
      text("<", probeX + 40, probeY + 25);               // Show out-of-range indicator
    if(pixelVal == 255 && fixedPoint[4] > fixedPoint[3]) // Clipped at top?
      text(">", probeX + 40, probeY + 25);               // Same
  }

  noSmooth();     // Clear any highlighted buttons
  stroke(0);
  noFill();
  for(sampleX = 0; sampleX < 8; ++sampleX)
    rect(butnsX + sampleX * 52, butnsY, 51, 24);

  sampleX = mouseX - butnsX;
  sampleY = mouseY - butnsY;
  if(sampleX >=0 && sampleX < 416 && sampleY >= 0 && sampleY < 24) { // Mouse over buttons?
    sampleX = sampleX / 52;                       // Map mouse X to button X space
    stroke(BGcolor + 64);
    rect(butnsX + sampleX * 52, butnsY, 51, 24);  // Highlight border around a button
  }
}

void keyPressed() {  // Load a different thermal BMP image based on keystroke
  switch(key) {
    case '.':   // Next image
      i = (i + 1) % fileCount;
      break;
    case ',':   // Prev Image
      i = (i + fileCount - 1) % fileCount;
      break;
    case '>':   // 16 images forward
      i = i + 16 < fileCount ? i + 16 : fileCount - 1;
      break;
    case '<':   // 16 images back
      i = i - 16 < 0 ? 0 : i - 16;
      break;
    case '/':   // Last image
      i = fileCount - 1;
      break;
    case 'm':   // First image
      i = 0;
      break;
  }
  loadBMPscreen(i);
}

void mousePressed() {
  int sampleX, sampleY;

  sampleX = mouseX - butnsX;
  sampleY = mouseY - butnsY;
  if(sampleX >=0 && sampleX < 416 && sampleY >= 0 && sampleY < 24) { // Is mouse over button row?
    sampleX = sampleX / 52;                       // Map mouse X to button X space

    switch(sampleX) {
      case 1:   // First image
        i = 0;
        break;
      case 2:   // 16 images back
        i = i - 16 < 0 ? 0 : i - 16;
        break;
      case 3:   // Prev Image
        i = (i + fileCount - 1) % fileCount;
        break;
      case 4:   // Next image
        i = (i + 1) % fileCount;
        break;
      case 5:   // 16 images forward
        i = i + 16 < fileCount ? i + 16 : fileCount - 1;
        break;
      case 6:   // Last image
        i = fileCount - 1;
        break;
      case 7:   // Change color map
        loadColorTable(colorMap = (colorMap + 1) % 5, 0); // Load color table
        break;
      default:  // Toggle C/F
        celsiusFlag = !celsiusFlag;
        break;
    }
    loadBMPscreen(i);
  }
}

void loadBMPscreen(int fileIndex) {
  int x, y;

  b = loadBytes(filenames[fileIndex]);   // Open a file and read its 8-bit data
  background(BGcolor);                   // Clear screen
  enlarge8bitColor();                    // Place colored enlarged image on screen

  for(x = 0; x < 5; ++x) {  // Rebuild 5 float values from next 4*n bytes in the file
    fixedPoint[x] = expandFloat(b[2360 + (x * 4) + 0], b[2360 + (x * 4) + 1],
                                b[2360 + (x * 4) + 2], b[2360 + (x * 4) + 3]);
  }
  y = ((b[2387] & 0xff) << 24) + ((b[2386] & 0xff) << 16)
    + ((b[2385] & 0xff) <<  8) +  (b[2384] & 0xff);       // Reassemble a milliseconds time stamp

  textSize(10);        // Print text labels for the frame stats
  smooth();
  fill(255);
  text(filenames[fileIndex], numbersX + 5, numbersY + 40); // Show current filename

  if(celsiusFlag)
    text("Frame\n\n\nSeconds\n\nDegrees C", numbersX + 5, numbersY + 8);
  else
    text("Frame\n\n\nSeconds\n\nDegrees F", numbersX + 5, numbersY + 8);

  text("Approximate temperatures based on 8-bit pixel values", probeX - 42, probeY + 52); // Show approximation disclaimer

  textSize(15);
  text(fileIndex, numbersX + 5, numbersY + 25);     // Print frame number
  text(float(y) * 0.001, numbersX, numbersY + 74);  // Print time stamp in seconds

  if(celsiusFlag) {      // Show 3 temps in Celsius
    fill(255, 128, 64);
    text(fixedPoint[4], numbersX, numbersY + 108);
    fill(255, 200, 64);
    text(fixedPoint[2], numbersX, numbersY + 128);
    fill(128, 128, 255);
    text(fixedPoint[0], numbersX, numbersY + 148);

  } else {               // or show them in Farenheit
    fill(255, 128, 64);
    text(fixedPoint[4] * 1.8 + 32.0, numbersX, numbersY + 108);
    fill(255, 200, 64);
    text(fixedPoint[2] * 1.8 + 32.0, numbersX, numbersY + 128);
    fill(128, 128, 255);
    text(fixedPoint[0] * 1.8 + 32.0, numbersX, numbersY + 148);
  }

  noSmooth();
  stroke(0);
  fill(BGcolor + 24);
  for(x = 0; x < 8; ++x)     // Draw 8 button rectangles
    rect(butnsX + x * 52, butnsY, 51, 24);
  for(x = 0; x < 50; ++x) {  // Paint a mini colormap gradient within last button
    y = int(map(x, 0, 50, 0, 255));
    stroke(colorPal[4 * y + 2] & 0xFF, colorPal[4 * y + 1] & 0xFF, colorPal[4 * y + 0] & 0xFF);
    line(butnsX + 365 + x, butnsY + 1, butnsX + 365 + x, butnsY + 23);
  }
  smooth();  // Add text labels to buttons
  fill(255);
  textSize(15);
  text("|<      <<       <         >        >>      >|", butnsX + 70, butnsY + 17);
  if(celsiusFlag)
    text("C", butnsX + 20, butnsY + 18);
  else
    text("F", butnsX + 20, butnsY + 18);
}

void enlarge8bitColor() {  // Convert a small gray BMP array and plot an enlarged colormapped version
  int x, y;

  noStroke();

  for(y = 0; y < 24; ++y) {   // Count all source pixels
    for(x = 0; x < 32; ++x) {
      int pixMid = b[54 + ((32 * y + x) +  0) * 3] & 0xFF;
      fill(colorPal[4 * pixMid + 2] & 0xFF, colorPal[4 * pixMid + 1] & 0xFF, colorPal[4 * pixMid + 0] & 0xFF);  // Get color from table
      rect(offsetX + 8 * x, offsetY + 8 * (23 - y), 8, 8);  // Draw a square pixel, bottom up
    }
  }
}

void loadColorTable(int choiceNum, int offset) {
  int i, x;

  switch(choiceNum) {
    case 1:     // Load 8-bit BMP color table with computed ironbow curves
      for(x = 0; x < 256; ++x) {
        float fleX = (float)x / 255.0;

        float fleG = 255.9 * (1.02 - (fleX - 0.72) * (fleX - 0.72) * 1.96);
        fleG = (fleG > 255.0) || (fleX > 0.75) ? 255.0 : fleG;  // Truncate curve
        i = (int)fleG;
        colorPal[offset + x * 4 + 2] = byte(i & 0xFF);    // Red vals

        fleG = fleX * fleX * 255.9;
        i = (int)fleG;
        colorPal[offset + x * 4 + 1] = byte(i & 0xFF);    // Grn vals

        fleG = 255.9 * (14.0 * (fleX * fleX * fleX) - 20.0 * (fleX * fleX) + 7.0 * fleX);
        fleG = fleG < 0.0 ? 0.0 : fleG;  // Truncate curve
        i = (int)fleG;
        colorPal[offset + x * 4 + 0] = byte(i & 0xFF);    // Blu vals
      }
      break;
    case 2:  // Compute quadratic "firebow" palette
      for(x = 0; x < 256; ++x) {
        float fleX = (float)x / 255.0;

        float fleG = 255.9 * (1.00 - (fleX - 1.0) * (fleX - 1.0));
        i = (int)fleG;
        colorPal[offset + x * 4 + 2] = byte(i & 0xFF);    // Red vals

        fleG = fleX < 0.25 ? 0.0 : (fleX - 0.25) * 1.3333 * 255.9;
        i = (int)fleG;
        colorPal[offset + x * 4 + 1] = byte(i & 0xFF);    // Grn vals

        fleG = fleX < 0.5 ? 0.0 : (fleX - 0.5) * (fleX - 0.5) * 1023.9;
        i = (int)fleG;
        colorPal[offset + x * 4 + 0] = byte(i & 0xFF);    // Blu vals
      }
      break;
    case 3:  // Compute "alarm" palette
      for(x = 0; x < 256; ++x) {
        float fleX = (float)x / 255.0;

        float fleG = 255.9 * (fleX < 0.875 ? 1.00 - (fleX * 1.1428) : 1.0);
        i = (int)fleG;
        colorPal[offset + x * 4 + 2] = byte(i & 0xFF);    // Red vals

        fleG = 255.9 * (fleX < 0.875 ? 1.00 - (fleX * 1.1428) : (fleX - 0.875) * 8.0);
        i = (int)fleG;
        colorPal[offset + x * 4 + 1] = byte(i & 0xFF);    // Grn vals

        fleG = 255.9 * (fleX < 0.875 ? 1.00 - (fleX * 1.1428) : 0.0);
        i = (int)fleG;
        colorPal[offset + x * 4 + 0] = byte(i & 0xFF);    // Blu vals
      }
      break;
    case 4:    // Grayscale, black hot 
      for(x = 0; x < 256; ++x) {
        colorPal[offset + x * 4 + 2] = byte(255 - x & 0xFF);    // Red vals
        colorPal[offset + x * 4 + 1] = byte(255 - x & 0xFF);    // Grn vals
        colorPal[offset + x * 4 + 0] = byte(255 - x & 0xFF);    // Blu vals
      }
      break;
    default:    // Grayscale, white hot 
      for(x = 0; x < 256; ++x) {
        colorPal[offset + x * 4 + 2] = byte(x & 0xFF);    // Red vals
        colorPal[offset + x * 4 + 1] = byte(x & 0xFF);    // Grn vals
        colorPal[offset + x * 4 + 0] = byte(x & 0xFF);    // Blu vals
      }
  }
}

// Rebuild a float from a fixed point decimal value encoded in 4 bytes
float expandFloat(byte m1, byte m2, byte e1, byte e2) {
  int fracPart;
  float floatPart;

  fracPart = ((e2 & 0xff) << 8) + (e1 & 0xff);   // Reassemble 16-bit value
  floatPart = (float)fracPart / 49152.0;         // Convert into fractional portion of float
  fracPart = ((m2 & 0xff) << 8) + (m1 & 0xff);   // Reassemble 16-bit value
  return ((float)fracPart + floatPart) - 1000.0; // Complete reconstructing original float
}

String[] listFileNames(String dir) {   // Return the filenames from a directory as an array of Strings
  File file = new File(dir);

  if (file.isDirectory()) {
    String names[] = file.list();
    return names;
  } else    // It's not a directory
    return null;
}