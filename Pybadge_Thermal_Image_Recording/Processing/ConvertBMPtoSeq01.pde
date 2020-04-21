// ConvertBMPtoSeq01 - Read and enlarge a modified 32x24 24-bit gray BMP file,
//                     saving 256x192 BMP images in 256 colors for converting to MOV.
// Ver. 1 - Fetch filenames and scan all suitable BMPs we find for their time/temp data,
//          to set the scale for graphing these numbers through the MOV.
 
import java.util.Date;
 
byte colorPal[], b[];     // Buffers for a color palette, and reading bytes from files
 
PImage img;
int i, fileCount = 0, frameTotal = 0, earlyFrame = 0, lastFrame = 0,
    hotLowFrame, hotHighFrame, coldLowFrame, coldHighFrame, targLowFrame, targHighFrame,
    framX1, framX2, coldY1, coldY2, targY1, targY2, hotY1, hotY2,
    offsetX = 153, offsetY = 6, numbersX = 40, numbersY = 30, graphX = 8, graphY = 342,
    histoX = 410, histoY = 342, histoH = 140, histoW = 64, BGcolor = 48;
float hottestLow, hottestHigh, coldestLow, coldestHigh, targetLow, targetHigh;
String[] filenames;
 
 
 
// Change the following values to customize the output images.
// "paletteChoice" selects a false color palette:
// 0 == Grayscale, white hot
// 1 == Ironbow
// 2 == Firebow
// 3 == Hot alarm
// 4 == Grayscale, black hot
int paletteChoice = 1;
boolean markersVisible = true, celsiusFlag = false, lirpSmoothing = true;
 
void setup() {
  int x, y;
  float fixedPoint[];
  String nameHead, nameTail;
 
  size(480, 360);      // Size must be the first statement
  background(BGcolor); // Clear the screen with a gray background
  noSmooth();
 
  colorPal = new byte[1024];        // Reserve a 1K color table
  loadColorTable(paletteChoice, 0); // Load color table
  fixedPoint = new float[5];        // Buffer for added fixed point values
 
  String path = sketchPath() + "/data";  // Read from the "/data" subdirectory
 
//  println("Listing filenames: ");
  filenames = listFileNames(path);
//  println(filenames);
  fileCount = filenames.length;
//  println(fileCount + " entries");
 
  if(fileCount < 1) {
    println("No images found.  Stopping.");
  } else {    // Filenames exist in the directory, convert what we can
 
// First pass: Read the embedded times/temps and find maxes/mins for graphing
    print("Counting through files: ");
    for(i = 0; i < fileCount; ++i) {   // Test each filename for conformity
      if((i & 0x3F) == 0)
        print(i + ", ");
      nameHead = filenames[i].substring(0, 3);
      nameTail = filenames[i].substring(8);
 
      if(nameHead.equals("frm") && nameTail.equals(".bmp") && int(filenames[i].substring(3, 8)) != 0) { // Source "frm_____.bmp" found?
        b = loadBytes(filenames[i]);   // Open a file and read its 8-bit data
 
        for(x = 0; x < 5; ++x) {  // Rebuild float values from next 4*n bytes in the file
          fixedPoint[x] = expandFloat(b[2360 + (x * 4) + 0], b[2360 + (x * 4) + 1],
                                      b[2360 + (x * 4) + 2], b[2360 + (x * 4) + 3]); // 2360 == headers + pixels + 2
        }
        y = ((b[2387] & 0xff) << 24) + ((b[2386] & 0xff) << 16)
          + ((b[2385] & 0xff) <<  8) +  (b[2384] & 0xff);   // Reassemble a uint32_t millis() stamp
 
        if(++frameTotal == 1) { // First frame found so far?
          coldestLow = coldestHigh = fixedPoint[0];
          targetLow  = targetHigh  = fixedPoint[2];  // Initialize all values
          hottestLow = hottestHigh = fixedPoint[4];
          hotLowFrame = hotHighFrame = coldLowFrame = coldHighFrame = targLowFrame = targHighFrame = earlyFrame = lastFrame = y;
        } else {   // Compare everything, update where necessary
 
          if(y < earlyFrame)
            earlyFrame = y;       // These will set the left and right bounds
          else if(y > lastFrame)  // of the temperature over time graphs
            lastFrame = y;
 
          if(fixedPoint[0] < coldestLow) {       // These will define the high and low bounds
            coldestLow = fixedPoint[0];
            coldLowFrame = y;
          } else if(fixedPoint[0] > coldestHigh) {
            coldestHigh = fixedPoint[0];
            coldHighFrame = y;
          }
 
          if(fixedPoint[2] < targetLow) {
            targetLow = fixedPoint[2];
            targLowFrame = y;
          } else if(fixedPoint[2] > targetHigh) {
            targetHigh = fixedPoint[2];
            targHighFrame = y;
          }
 
          if(fixedPoint[4] < hottestLow) {
            hottestLow = fixedPoint[4];
            hotLowFrame = y;
          } else if(fixedPoint[4] > hottestHigh) {
            hottestHigh = fixedPoint[4];
            hotHighFrame = y;
          }
        }
      }
    }
    println(i + ", done.\n");
 
// The high and low points of three datasets are found, display them
    println("Frame times " + earlyFrame + " to " + lastFrame + " totaling " + (lastFrame - earlyFrame));
    println("Cold values " + coldestLow + " at " + coldLowFrame + " to " + coldestHigh + " at " + coldHighFrame);
    println("Targ values " +  targetLow + " at " + targLowFrame + " to " +  targetHigh + " at " + targHighFrame);
    println("Hot values  " + hottestLow + " at " +  hotLowFrame + " to " + hottestHigh + " at " +  hotHighFrame);
 
    stroke(BGcolor + 48);
    for(y = 0; y <= 140; y += 35)
      line(graphX, graphY - y, graphX + 400, graphY - y);  // Draw a generic grid for the time graph
    for(x = 0; x <= 400; x += 40)
      line(graphX + x, graphY - 140, graphX + x, graphY);
 
    noStroke();     // Text labels for the top & bottom temp values of the graph
    textSize(10);
    fill(255);
    if(celsiusFlag) {
      text(hottestHigh, graphX + 402, graphY - 142);
      text(coldestLow,  graphX + 402, graphY +  12);
    } else {
      text(hottestHigh * 1.8 + 32.0, graphX + 402, graphY - 142);
      text(coldestLow * 1.8 + 32.0,  graphX + 402, graphY +  12);
    }
 
    fill(BGcolor + 128);           // Predraw 6 little high/low markers in the graph space
    rect(graphX + 400 * (coldLowFrame  - earlyFrame) / (lastFrame - earlyFrame) - 1,
         graphY - int((coldestLow -  coldestLow) / (coldestLow - hottestHigh) * 140.0) - 1, 3, 3);
    rect(graphX + 400 * (coldHighFrame - earlyFrame) / (lastFrame - earlyFrame) - 1,
         graphY - int((coldestLow - coldestHigh) / (coldestLow - hottestHigh) * 140.0) - 1, 3, 3);
 
    rect(graphX + 400 * (targLowFrame  - earlyFrame) / (lastFrame - earlyFrame) - 1,
         graphY - int((coldestLow -   targetLow) / (coldestLow - hottestHigh) * 140.0) - 1, 3, 3);
    rect(graphX + 400 * (targHighFrame - earlyFrame) / (lastFrame - earlyFrame) - 1,
         graphY - int((coldestLow -  targetHigh) / (coldestLow - hottestHigh) * 140.0) - 1, 3, 3);
 
    rect(graphX + 400 * (hotLowFrame   - earlyFrame) / (lastFrame - earlyFrame) - 1,
         graphY - int((coldestLow -  hottestLow) / (coldestLow - hottestHigh) * 140.0) - 1, 3, 3);
    rect(graphX + 400 * (hotHighFrame  - earlyFrame) / (lastFrame - earlyFrame) - 1,
         graphY - int((coldestLow - hottestHigh) / (coldestLow - hottestHigh) * 140.0) - 1, 3, 3);
  }
  i = 0;
}
 
// Second pass: Read each frame again, plot color mapped enlarged image, temperature values and graph, save each frame
void draw() {
  int x, y, histogram[];
  float tempY, fixedPoint[];
  String nameHead, nameTail;
 
  noSmooth();
  fixedPoint = new float[5];   // Buffer for appended fixed point values
  histogram  = new int[256];   // Buffer for color histogram
  for(x = 0; x < 256; ++x)
    histogram[x] = 0;          // Initialize histogram
 
  if(i < fileCount) {   // Test each filename for conformity
    nameHead = filenames[i].substring(0, 3);
    nameTail = filenames[i].substring(8);
 
    if(nameHead.equals("frm") && nameTail.equals(".bmp") && int(filenames[i].substring(3, 8)) != 0) { // Source "frm_____.bmp" found?
      b = loadBytes(filenames[i]);   // Open a file and read its 8-bit data
//      println(i + " " + filenames[i]);
      enlarge8bitColor();            // Place colored enlarged image on screen
 
      for(x = 0; x < 5; ++x) {  // Rebuild float values from next 4*n bytes in the file
        fixedPoint[x] = expandFloat(b[2360 + (x * 4) + 0], b[2360 + (x * 4) + 1],
                                    b[2360 + (x * 4) + 2], b[2360 + (x * 4) + 3]);
      }
      y = ((b[2387] & 0xff) << 24) + ((b[2386] & 0xff) << 16)
        + ((b[2385] & 0xff) <<  8) +  (b[2384] & 0xff);       // Reassemble a milliseconds time stamp
 
      smooth();
      framX2 = graphX + 400 * (y - earlyFrame) / (lastFrame - earlyFrame);
      coldY2 = graphY - int((coldestLow - fixedPoint[0]) / (coldestLow - hottestHigh) * 140.0); // Map data values into graph space
      targY2 = graphY - int((coldestLow - fixedPoint[2]) / (coldestLow - hottestHigh) * 140.0);
      hotY2  = graphY - int((coldestLow - fixedPoint[4]) / (coldestLow - hottestHigh) * 140.0);
 
      if(i == 0) {
        framX1 = framX2;  // Set starting points for 3 graphs 
        coldY1 = coldY2;
        targY1 = targY2;
        hotY1 = hotY2;
      }
 
      stroke(128, 128, 255);
      line(framX1, coldY1, framX2, coldY2);  // Graph cold data point
      stroke(255, 200, 64);
      line(framX1, targY1, framX2, targY2);  // Graph center data point
      stroke(255, 128, 64);
      line(framX1,  hotY1, framX2,  hotY2);  // Graph hot data point
 
      framX1 = framX2;  // Remember endpoints of graphed lines 
      coldY1 = coldY2;
      targY1 = targY2;
      hotY1  = hotY2;
 
      noStroke();          // Print key values onscreen for current frame
      fill(BGcolor);
      rect(numbersX, numbersY, 82, 152);  // Erase number region
 
      fill(BGcolor + 32);  // A color to highlight any extreme values
      if(y == hotLowFrame || y == hotHighFrame)
        rect(numbersX, numbersY + 95, 80, 16);
      if(y == targLowFrame || y == targHighFrame)
        rect(numbersX, numbersY + 115, 80, 16);
      if(y == coldLowFrame || y == coldHighFrame)
        rect(numbersX, numbersY + 135, 80, 16);
 
      textSize(10);
      fill(255);
      text(filenames[i], numbersX + 5, numbersY + 40); // Show current filename
 
      if(celsiusFlag)
        text("Frame\n\n\nElapsed sec\n\nDegrees C", numbersX + 5, numbersY + 8);
      else
        text("Frame\n\n\nElapsed sec\n\nDegrees F", numbersX + 5, numbersY + 8);
 
      textSize(15);
      text(i, numbersX + 5, numbersY + 25);                          // Print frame number
      text(float(y - earlyFrame) * 0.001, numbersX, numbersY + 74);  // Print elapsed time
 
      if(celsiusFlag) {      // Print temps in Celsius
        fill(255, 128, 64);
        text(fixedPoint[4], numbersX, numbersY + 108);
        fill(255, 200, 64);
        text(fixedPoint[2], numbersX, numbersY + 128);
        fill(128, 128, 255);
        text(fixedPoint[0], numbersX, numbersY + 148);
      } else {               // or print them in Farenheit
        fill(255, 128, 64);
        text(fixedPoint[4] * 1.8 + 32.0, numbersX, numbersY + 108);
        fill(255, 200, 64);
        text(fixedPoint[2] * 1.8 + 32.0, numbersX, numbersY + 128);
        fill(128, 128, 255);
        text(fixedPoint[0] * 1.8 + 32.0, numbersX, numbersY + 148);
      }
 
      for(x = 0; x < 768; ++x)
        ++histogram[b[54 + 3 * x] & 0xFF];  // Count all colors
      framX2 = histogram[0];
      for(x = 1; x < 256; ++x) {            // Find most numerous color
        if(histogram[x] > framX2) {
          framX2 = histogram[x];
          targY2 = x;
        }
      }
 
      fill(BGcolor);
      rect(histoX, histoY - 140, histoW, histoH + 1);  // Erase histogram region
 
      for(y = 0; y < 256; ++y) {
        if(histogram[y] > 0) {
          tempY = float(y) * (fixedPoint[3] - fixedPoint[1]) / 255.0 + fixedPoint[1];    // Convert a 8-bit value to a temperature
          tempY = float(histoH) * (coldestLow - tempY) / (coldestLow - hottestHigh);     // Position it on the graph Y axis
          stroke(colorPal[4 * y + 2] & 0xFF, colorPal[4 * y + 1] & 0xFF, colorPal[4 * y + 0] & 0xFF);  // Color map the stroke
          line(histoX, histoY - int(tempY), histoX + (histoW - 1) * histogram[y] / framX2, histoY - int(tempY)); // Draw a line proportional to the pixel count  
        }
 
        noStroke();
        noSmooth();
        textSize(10);
        if(targY2 < 0x80) // Histogram peak in the dark side?
          fill(255);      // Set contrasting test to white
        else
          fill(0);
 
        tempY = float(targY2) * (fixedPoint[3] - fixedPoint[1]) / 255.0 + fixedPoint[1];    // Convert a 8-bit value to a temperature
        if(celsiusFlag)    // Print the Y-positioned float value in C?
          text(tempY, histoX, histoY + 3 - int(float(histoH) * (coldestLow - tempY) / (coldestLow - hottestHigh)));
        else
          text(tempY * 1.8 + 32.0, histoX, histoY + 3 - int(float(histoH) * (coldestLow - tempY) / (coldestLow - hottestHigh)));
      }
      saveFrame("mov#####.jpg");  // Save the image into a sequence for Movie Maker
    }
    ++i;
  }
}
 
void enlarge8bitColor() {  // Convert a small gray BMP array and plot an enlarged colormapped version
  int x, y;
 
  if(lirpSmoothing) {           // Bilinear interpolation?
    for(y = 0; y < 23; ++y) {   // Count the source pixels less one
      for(x = 0; x < 31; ++x) {
        for(int yLirp = 0; yLirp < 9; ++yLirp) {
          int corner0 = b[54 + ((32 * y + x) + 32) * 3] & 0xFF;
          int corner1 = b[54 + ((32 * y + x) +  0) * 3] & 0xFF;
          int pixLeft  = (corner0 * yLirp + corner1 * (8 - yLirp)) >> 3;  // Lirp 1 endpoint from 2 L pixels,
 
          int corner2 = b[54 + ((32 * y + x) + 33) * 3] & 0xFF;
          int corner3 = b[54 + ((32 * y + x) +  1) * 3] & 0xFF;
          int pixRight = (corner2 * yLirp + corner3 * (8 - yLirp)) >> 3;  // and the other from 2 R pixels
 
          for(int xLirp = 0; xLirp < 9; ++xLirp) {
            int pixMid = (pixRight * xLirp + pixLeft * (8 - xLirp)) >> 3;         // Lirp between lirped endpoints, bilinear interp
            stroke(colorPal[4 * pixMid + 2] & 0xFF, colorPal[4 * pixMid + 1] & 0xFF, colorPal[4 * pixMid + 0] & 0xFF);
            point(offsetX + 4 + 8 * x + xLirp, offsetY + 188 - (8 * y + yLirp));  // Draw a pixel, bottom up
          }
        }
      }
    }
 
    for(y = 0; y < 192; ++y) {   // Pad out the empty side pixels
      stroke(get(offsetX + 4, offsetY + y));
      line(offsetX + 0, offsetY + y, offsetX + 3, offsetY + y);
      stroke(get(offsetX + 252, offsetY + y));
      line(offsetX + 253, offsetY + y, offsetX + 255, offsetY + y);
    }
    for(x = 0; x < 256; ++x) {
      stroke(get(offsetX + x, offsetY + 4));
      line(offsetX + x, offsetY + 0, offsetX + x, offsetY + 3);
      stroke(get(offsetX + x, offsetY + 188));
      line(offsetX + x, offsetY + 189, offsetX + x, offsetY + 191);
    }
  } else {    // Plain square pixels
    noStroke();
 
    for(y = 0; y < 24; ++y) {   // Count all source pixels
      for(x = 0; x < 32; ++x) {
        int pixMid = b[54 + ((32 * y + x) +  0) * 3] & 0xFF;
        fill(colorPal[4 * pixMid + 2] & 0xFF, colorPal[4 * pixMid + 1] & 0xFF, colorPal[4 * pixMid + 0] & 0xFF);  // Get color from table
        rect(offsetX + 8 * x, offsetY + 8 * (23 - y), 8, 8);  // Draw a pixel, bottom up
      }
    }
  }
 
  if(markersVisible) {  // Show the green marker crosses?
    stroke(0, 192, 0);  // Deep green
 
    y = ((b[2381] & 0xff) <<  8) +  (b[2380] & 0xff);   // Reassemble 16-bit addresses of cold / hot pixels
    line(offsetX + 8 * (y & 31) + 1, offsetY + 188 - 8 * (y >> 5), offsetX + 8 * (y & 31) + 7, offsetY + 188 - 8 * (y >> 5));
    line(offsetX + 8 * (y & 31) + 4, offsetY + 185 - 8 * (y >> 5), offsetX + 8 * (y & 31) + 4, offsetY + 191 - 8 * (y >> 5));
 
    y = ((b[2383] & 0xff) <<  8) +  (b[2382] & 0xff);
    line(offsetX + 8 * (y & 31) + 1, offsetY + 188 - 8 * (y >> 5), offsetX + 8 * (y & 31) + 7, offsetY + 188 - 8 * (y >> 5));
    line(offsetX + 8 * (y & 31) + 4, offsetY + 185 - 8 * (y >> 5), offsetX + 8 * (y & 31) + 4, offsetY + 191 - 8 * (y >> 5));
 
    y = 400;
    line(offsetX + 8 * (y & 31) + 1, offsetY + 188 - 8 * (y >> 5), offsetX + 8 * (y & 31) + 7, offsetY + 188 - 8 * (y >> 5));
    line(offsetX + 8 * (y & 31) + 4, offsetY + 185 - 8 * (y >> 5), offsetX + 8 * (y & 31) + 4, offsetY + 191 - 8 * (y >> 5));
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
