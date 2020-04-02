// ConvertBMPto8bit - Read and enlarge a modified 32x24 24-bit gray BMP file,
//                    write an upscaled 256x192 BMP image with a 256 color table.
// Ver. 2 - Fetch filenames and convert all suitable BMPs we find.
//          Builds sequences suitable for online animated GIF converters

import java.util.Date;

// BMP File Header, little end first
int BmpPSPHead[] = {
 0x42, 0x4D,             // "BM" in hex
 0x36, 0xC4, 0x00, 0x00, // File size, 50230
 0x00, 0x00,             // reserved for app data 1
 0x00, 0x00,             // reserved for app data 2
 0x36, 0x04, 0x00, 0x00  // Offset of pixel 0, 1078
};

// BMP 8-bit DIB Header, little end first
int DIBHeadPSP1[] = {
 0x28, 0x00, 0x00, 0x00,  // Header size, 40
 0x00, 0x01, 0x00, 0x00,  // pixel width, 256
 0xC0, 0x00, 0x00, 0x00,  // pixel height, 192
 0x01, 0x00,              // color planes, 1
 0x08, 0x00,              // bits per pixel, 8
 0x00, 0x00, 0x00, 0x00,  // Compression method, 0==none
 0x00, 0x00, 0x00, 0x00,  // Raw bitmap data size, dummy 0
 0x12, 0x0B, 0x00, 0x00,  // Pixels per meter H, 2834
 0x12, 0x0B, 0x00, 0x00,  // Pixels per meter V, 2834
 0x00, 0x00, 0x00, 0x00,  // Colors in palette, 0==default 2^n
 0x00, 0x00, 0x00, 0x00   // Number of important colors, 0
};

byte outBytes[], b[];     // Buffer for the input file bytes

PImage img;  // Declare variable of type PImage
int fileCount = 0, imageIndex = 0;
String[] filenames;

// "paletteChoice" selects a false color palette:
// 0 == Grayscale, white hot
// 1 == Ironbow
// 2 == Firebow
// 3 == Hot alarm
// 4 == Grayscale, black hot
int paletteChoice = 1;

void setup() {
  int i, j, x, y;
  String nameHead, nameTail;

  size(256, 192);  // Size must be the first statement
//  noStroke();
  frameRate(5);
  background(0);   // Clear the screen with a black background

  outBytes = new byte[50230]; // 54 header + 1K colors + 12K pixels

  String path = sketchPath() + "/data"; // Read from the "/data" subdirectory

  println("Listing filenames: ");
  filenames = listFileNames(path);
  println(filenames);
  fileCount = filenames.length;
  println(fileCount + " entries");

  if(fileCount < 1) {
    println("No images found.  Stopping.");
  } else {    // Filenames exist in the directory
    for(i = 0; i < fileCount; ++i) {   // Test each name
      nameHead = filenames[i].substring(0, 3);
      nameTail = filenames[i].substring(8);
      j = int(filenames[i].substring(3, 8));

      if(nameHead.equals("frm") && nameTail.equals(".bmp") && j != 0)   // Source "frm_____.bmp" found?
        enlarge8bit(i);    // Process and write an enlarged 8-bit version
    }
  }
  noLoop();
}

void draw() {
  int countX, countY;

  noSmooth();

  for(countY = 0; countY < 192; ++countY) {
    for(countX = 0; countX < 256; ++countX) {
      stroke(0xFF & outBytes[1078 + (countY * 256 + countX)]); // Color from BMP buffer 
      point(countX, 191 - countY);                             // Draw a pixel, bottom up
    }
  }
}

void enlarge8bit(int fileNumber) {  // Read a small gray "frm" BMP image and write an enlarged colormapped "out" BMP
  int i, x, y;

  b = loadBytes(filenames[fileNumber]);   // Open a file and read its 8-bit data

  for(i = 0; i < 14; ++i)
    outBytes[i] = byte(BmpPSPHead[i] & 0xFF);        // Copy BMP header 1 into output buffer
  for(i = 0; i < 40; ++i)
    outBytes[i + 14] = byte(DIBHeadPSP1[i] & 0xFF);  // Copy header 2

  loadColorTable(paletteChoice, 54);  // Load color table, 54 byte BMP header offset

  for(y = 0; y < 23; ++y) {        // Bilinear interpolation, count the source pixels less one
    for(x = 0; x < 31; ++x) {
      for(int yLirp = 0; yLirp < 9; ++yLirp) {
        int corner0 = b[54 + ((32 * y + x) + 32) * 3] & 0xFF;
        int corner1 = b[54 + ((32 * y + x) +  0) * 3] & 0xFF;
        int pixLeft  = (corner0 * yLirp + corner1 * (8 - yLirp)) >> 3;  // Lirp 1 endpoint from 2 L pixels,

        int corner2 = b[54 + ((32 * y + x) + 33) * 3] & 0xFF;
        int corner3 = b[54 + ((32 * y + x) +  1) * 3] & 0xFF;
        int pixRight = (corner2 * yLirp + corner3 * (8 - yLirp)) >> 3;  // and the other from 2 R pixels

        for(int xLirp = 0; xLirp < 9; ++xLirp) {
          int pixMid = (pixRight * xLirp + pixLeft * (8 - xLirp)) >> 3; // Lirp between lirped endpoints, bilinear interp
          outBytes[1078 + y * 2048 + x * 8 + yLirp * 256 + xLirp + 771] = byte(pixMid & 0xFF);
        }
      }
    }
  }
  for(y = 0; y < 192; ++y) {   // Pad out the empty side pixels
    for(x = 0; x < 4; ++x) {
      outBytes[1078 + (3 - x) + 256 * y] = outBytes[1082 + 256 * y];
      outBytes[1330 +      x  + 256 * y] = outBytes[1329 + 256 * y];
    }
  }
  for(x = 0; x < 256; ++x) {   // Pad out the empty above/below pixels
    for(y = 0; y < 4; ++y) {
      outBytes[ 1078 + 256 * (3 - y) + x] = outBytes[ 2102 + x];
      outBytes[49206 + 256 *      y  + x] = outBytes[48950 + x];
    }
  }

  saveBytes("data/out" + filenames[fileNumber].substring(3), outBytes);   // Save a recolored 8-bit BMP as "out_____.bmp"
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
        outBytes[offset + x * 4 + 2] = byte(i & 0xFF);    // Red vals

        fleG = fleX * fleX * 255.9;
        i = (int)fleG;
        outBytes[offset + x * 4 + 1] = byte(i & 0xFF);    // Grn vals

        fleG = 255.9 * (14.0 * (fleX * fleX * fleX) - 20.0 * (fleX * fleX) + 7.0 * fleX);
        fleG = fleG < 0.0 ? 0.0 : fleG;  // Truncate curve
        i = (int)fleG;
        outBytes[offset + x * 4 + 0] = byte(i & 0xFF);    // Blu vals
      }
      break;
    case 2:  // Compute quadratic "firebow" palette
      for(x = 0; x < 256; ++x) {
        float fleX = (float)x / 255.0;

        float fleG = 255.9 * (1.00 - (fleX - 1.0) * (fleX - 1.0));
        i = (int)fleG;
        outBytes[offset + x * 4 + 2] = byte(i & 0xFF);    // Red vals

        fleG = fleX < 0.25 ? 0.0 : (fleX - 0.25) * 1.3333 * 255.9;
        i = (int)fleG;
        outBytes[offset + x * 4 + 1] = byte(i & 0xFF);    // Grn vals

        fleG = fleX < 0.5 ? 0.0 : (fleX - 0.5) * (fleX - 0.5) * 1023.9;
        i = (int)fleG;
        outBytes[offset + x * 4 + 0] = byte(i & 0xFF);    // Blu vals
      }
      break;
    case 3:  // Compute "alarm" palette
      for(x = 0; x < 256; ++x) {
        float fleX = (float)x / 255.0;

        float fleG = 255.9 * (fleX < 0.875 ? 1.00 - (fleX * 1.1428) : 1.0);
        i = (int)fleG;
        outBytes[offset + x * 4 + 2] = byte(i & 0xFF);    // Red vals

        fleG = 255.9 * (fleX < 0.875 ? 1.00 - (fleX * 1.1428) : (fleX - 0.875) * 8.0);
        i = (int)fleG;
        outBytes[offset + x * 4 + 1] = byte(i & 0xFF);    // Grn vals

        fleG = 255.9 * (fleX < 0.875 ? 1.00 - (fleX * 1.1428) : 0.0);
        i = (int)fleG;
        outBytes[offset + x * 4 + 0] = byte(i & 0xFF);    // Blu vals
      }
      break;
    case 4:    // Grayscale, black hot 
      for(x = 0; x < 256; ++x) {
        outBytes[offset + x * 4 + 2] = byte(255 - x & 0xFF);    // Red vals
        outBytes[offset + x * 4 + 1] = byte(255 - x & 0xFF);    // Grn vals
        outBytes[offset + x * 4 + 0] = byte(255 - x & 0xFF);    // Blu vals
      }
      break;
    default:    // Grayscale, white hot 
      for(x = 0; x < 256; ++x) {
        outBytes[offset + x * 4 + 2] = byte(x & 0xFF);    // Red vals
        outBytes[offset + x * 4 + 1] = byte(x & 0xFF);    // Grn vals
        outBytes[offset + x * 4 + 0] = byte(x & 0xFF);    // Blu vals
      }
  }
}

String[] listFileNames(String dir) {   // Return the filenames from a directory as an array of Strings
  File file = new File(dir);

  if (file.isDirectory()) {
    String names[] = file.list();
    return names;
  } else    // It's not a directory
    return null;
}