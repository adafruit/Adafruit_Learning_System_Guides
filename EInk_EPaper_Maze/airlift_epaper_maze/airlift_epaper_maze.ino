/* Program to automatically generate maze puzzles
 *
 * For use with Adafruit Metro M4 Express Airlift or Metro M4 and tricolor e-Paper Display Shield
 * 
 * Adafruit invests time and resources providing this open source code.
 * Please support Adafruit and open source hardware by purchasing
 * products from Adafruit.com!
 * 
 * Written by Dan Cogliano for Adafruit Industries
 * Copyright (c) 2019 Adafruit Industries MIT License, all text must be preserved
 */

#include <stdlib.h>
#include <stdio.h>

#include <Adafruit_GFX.h>    // Core graphics library
#include <Adafruit_EPD.h>
#include <Adafruit_NeoPixel.h>
#define SRAM_CS     8
#define EPD_CS      10
#define EPD_DC      9  
#define EPD_RESET -1
#define EPD_BUSY -1

#define NEOPIXELPIN   40

/* This is for the 2.7" tricolor EPD */
Adafruit_IL91874 gfx(264, 176 ,EPD_DC, EPD_RESET, EPD_CS, SRAM_CS, EPD_BUSY);

Adafruit_NeoPixel neopixel = Adafruit_NeoPixel(1, NEOPIXELPIN, NEO_GRB + NEO_KHZ800);

#define MEM_MAX    20000

// print character to use when printing to terminal
#define BLOCK_CHAR 'X'

#define BOTTOM  0x01
#define RIGHT 0x02
#define TRUE  1
#define FALSE 0

// convert block # to x, y coordinate
#define GETX(item,width) (item % width)
#define GETY(item,width) (item / width)
#define COORD(item,width)(String("[") + String(GETX(item,width)) + "," + String(GETY(item,width)) + String("]"))

/* global variables defined here */
char *maze=NULL;              // pointer to maze wall data
uint16_t *mazepath=NULL;      // pointer to maze path data
uint16_t *mazesolution=NULL;  // pointer to maze solution
uint16_t solutioncount = 0;

int sizex=0, sizey=0;     /* maze size */
int cellsize = 10; // larger the cellsize, easier the puzzle, in pixels
int lwidth = 3; // maze wall width, in pixels

/*
   init_maze(cs, lw) initializes maze memory.
   cs - cell size in pixels (smaller cell = harder maze)
   lw - line width in pixels
   example: init_maze(7,2) will use 7 pixel boxes with 2 pixel maze wall width
     and 3 pixel solution line width (cs - lw - 2)
   Maze size is based on cs value and ePaper screen size
*/
void init_maze(int cs, int lw)
{
  // use max size allowable
  cellsize = cs;
  lwidth = lw;
  sizex = gfx.width()/cellsize;
  sizey = gfx.height()/cellsize;  
  Serial.println("maze size: " + String(sizex) + " x " + String(sizey));
  if(sizex < 1 || sizey < 1 || (long)sizex*sizey > MEM_MAX)
  {
    Serial.println("Invalid values entered for maze size\n");
    Serial.println("Maze must be at least 4 x 4\n");
    exit(EXIT_FAILURE);
  }
  long incr;
  for(incr=0; incr < (gfx.width()/5) *  (gfx.height()/5); incr++)
  {
    if(incr==0)
      maze[incr]=0;
    else if(incr < sizex)
      maze[incr]=BOTTOM;
    else if((incr%sizex)==0)
      maze[incr]=RIGHT;
    else
      maze[incr]=BOTTOM|RIGHT;
    mazepath[incr]=incr;
  }
}

/*
 * getDirection(pos1, pos2) get the direction between two points
 * return 1: x direction
 *        2: y direction
 */
int getDirection(uint16_t pos1, uint16_t pos2)
{
  int x1, y1, x2, y2, diffx, diffy;
  x1 = GETX(pos1,sizex);
  y1 = GETY(pos1,sizex);  
  x2 = GETX(pos2,sizex);
  y2 = GETY(pos2,sizex);

  diffx = x2 - x1;
  diffy = y2 - y1;

  //Serial.println( "getDirection: " + COORD(pos1,sizex) + "," + COORD(pos2,sizex) + "," + String(diffx) + "," + String(diffy));
  if(diffy == 0)
    return 1;
  if(diffx == 0)
    return 2;
  return 0; //diagonal? 
}

/*
 * solve_r() - recursive solve routine, called by solve()
 */
bool solve_r(uint16_t finish, uint16_t pos, uint16_t prevpos, uint8_t dir)
{
  if(pos == prevpos)
  {
    Serial.println("same square, backing up");
    solutioncount--;
    // same square, need to back up from here
    return false;
  }
  mazesolution[solutioncount++] = pos;
  if(pos == finish)
  {
    Serial.println("Solved in " + String(solutioncount) + " moves");
    return true;
  }
  uint16_t posx, posy, newx, newy, newpos;  
  /*
   * directions:
   * 0: north
   * 1: west
   * 2: south
   * 3: east
   */
   posy = GETY(pos, sizex);
   posx = GETX(pos, sizex);
   //Serial.println("trying square " + COORD(pos, sizex) + " at direction " + dir);
   switch(dir)
   {
   case 0: // north
      newx = posx;
      newy = posy - 1;
      newpos = newy * sizex + newx;
      if((maze[newpos] & BOTTOM) == 0)
      {
        return solve_r(finish, newpos, pos, 3);
      }
      break;
   case 1: // west
      newx = posx - 1;
      newy = posy;
      newpos = newy * sizex + newx;
      if((maze[newpos] & RIGHT) == 0)
      {
        return solve_r(finish, newpos, pos, 0);
      }
      break;
   case 2: // south
      newx = posx;
      newy = posy + 1;
      newpos = newy * sizex + newx;
      if((maze[pos] & BOTTOM) == 0)
      {
        return solve_r(finish, newpos, pos, 1);
      }
      break;
   case 3: // east
      newx = posx + 1;
      newy = posy;
      newpos = newy * sizex + newx;
      if((maze[pos] & RIGHT) == 0)
      {
        return solve_r(finish, newpos, pos, 2);
      }
      break;
   }
   dir = (dir + 1) %4;
   //Serial.println("next direction " + String(dir));
   solutioncount--;
   return solve_r(finish, pos, prevpos, dir);
}

/*
 * solve() - solve the maze
 */
void solve()
{
  uint16_t start = 0;
  uint16_t finish = 0;

  for(int i = 1; i < sizex; i++)
  {
    if((maze[i] & BOTTOM) == 0)
    {
      start = i + sizex;// start at row below
      break;
    }
  }
  for(int i = (sizey-1)*sizex + 1; i < (sizey*sizex); i++)
  {
    if((maze[i] & BOTTOM) == 0)
    {
      finish = i;
      break;
    }
  }
  solutioncount = 0;
  //Serial.println("maze start: " + COORD(start, sizex) + ", finish: " + COORD(finish, sizex));
  mazesolution[solutioncount++] = start;
  solve_r(finish, start, start - gfx.width(), 1);
  
  // remove dead end moves
  int solutionpos = 0;
  while(solutionpos < solutioncount)
  {
    //Serial.println("solution pos: " + String(solutionpos) + COORD(mazesolution[solutionpos], sizex) 
    //  + ", solution count: " + String(solutioncount));
    for(int i = solutioncount - 1; i > solutionpos; i--)
    {
      if(mazesolution[solutionpos] == mazesolution[i])
      {
        // remove dead end paths
        //Serial.println("removing " + String(i - solutionpos) + " duplicate path items");
        for(int j = 0; j < (solutioncount - solutionpos); j++)
        {          
          mazesolution[solutionpos + j] = mazesolution[i + j];
        }
        solutioncount -= i - solutionpos;
      }
    }
    solutionpos++;
  }
  Serial.println("Solution reduced to " + String(solutioncount) + " moves");

  /*
  // print out solution
  for(int i = 0; i < solutioncount; i++)
  {
    Serial.println(String(i) + ": " + COORD(mazesolution[i], sizex));
  }
  */
}
/*
 * print_epaper_maze() prints the maze on the ePaper device, optionally showing solution
 */
void print_epaper_maze(bool showsolution = false)
{
  int xcenter = 0 - cellsize/2;// + (gfx.width() - sizex*cellsize)/2;
  int ycenter = 0 - cellsize/2;// + (gfx.height() - sizey*cellsize) / 2;
  Serial.println("maze centering adjustment: " + String(xcenter)+ ", " + String(ycenter));
  gfx.powerUp();
  gfx.clearBuffer();
  neopixel.setPixelColor(0, neopixel.Color(0, 255, 0));
  neopixel.show();

  // draw horizontal lines
  for(int incry = 0; incry < sizey; incry++)
  {
    int xstart = -1;
    int xend = -1;
    for(int incrx = 0; incrx < sizex; incrx++)
    {
      if((*(maze+incry*sizex+incrx)&BOTTOM)!=0 && xstart == -1)
      {
        xstart = incrx;      
      }
      else if((*(maze+incry*sizex+incrx)&BOTTOM)==0 && xstart != -1)
      {
        xend = incrx;
        gfx.fillRect(xcenter + xstart*cellsize,ycenter + (incry+1)*cellsize,(xend - xstart)*cellsize+lwidth,lwidth,EPD_BLACK);
        xstart = -1;
        xend = -1;
      }
    }   
    if(xstart != -1)
    {
      // finish line
      xend = sizex;
      gfx.fillRect(xcenter + xstart*cellsize,ycenter + (incry+1)*cellsize,(xend - xstart)*cellsize+lwidth,lwidth,EPD_BLACK);
      xstart = -1;
      xend = -1;
    }
  }

  // draw vertical lines
  for(int incrx = 0; incrx < sizex; incrx++)
  {
    int ystart = -1;
    int yend = -1;
    for(int incry = 0; incry < sizey; incry++)
    {
      if((*(maze+incry*sizex+incrx)&RIGHT)!=0 && incry > 0 && ystart == -1)
      {
        ystart = incry;      
      }
      else if((*(maze+incry*sizex+incrx)&RIGHT)==0 && incry > 0 && ystart != -1)
      {
        yend = incry;
        gfx.fillRect(xcenter + (incrx+1)*cellsize,ycenter + ystart*cellsize,lwidth,(yend - ystart)*cellsize+lwidth,EPD_BLACK);
        ystart = -1;
        yend = -1;
      }
    }
    if(ystart != -1)
    {
      // finish line
      yend = sizey;
      gfx.fillRect(xcenter + (incrx+1)*cellsize,ycenter + ystart*cellsize,lwidth,(yend - ystart)*cellsize+lwidth,EPD_BLACK);
    }
  }

  if(showsolution)
  {
    /*
    // mouse droppings version
    for(int i = 0; i < solutioncount; i++)
    {
      gfx.fillRect(xcenter + GETX(mazesolution[i],sizex) * cellsize + lwidth, ycenter + GETY(mazesolution[i],sizex) * cellsize + lwidth, cellsize - lwidth, cellsize - lwidth, EPD_RED);      
    }
    */
    
    // line drawn version
    int rectx, recty, rectwidth, rectheight, rectstart, rectend;
    int dir;
    int linestart = mazesolution[0];
    int lineend = mazesolution[1];
    int lastdir = getDirection(linestart,lineend);
    int i = 1;
    
    // draw startline
    rectx = xcenter + GETX(mazesolution[0],sizex)*cellsize + lwidth + 1;
    recty = 0 - ycenter;
    rectwidth = cellsize - lwidth - 2;
    rectheight = ycenter + cellsize + lwidth + 1;
    gfx.fillRect(rectx, recty, rectwidth, rectheight, EPD_RED);
    //Serial.println("starting rectangle @ " + String(rectx) + "," + String(recty) + ": " + String(rectwidth) + " by " + String(rectheight));
        
    while(i < solutioncount)
    {
      lineend = mazesolution[i];
      if ((dir = getDirection(linestart,mazesolution[i+1])) != lastdir)
      {
        rectstart = linestart;
        rectend = lineend;
        if(((GETX(lineend,sizex) - GETX(linestart,sizex)) < 0) || ((GETY(lineend,sizex) - GETY(linestart,sizex)) > 0))
        {
          rectstart = lineend;
          rectend = linestart;
        }
        switch(lastdir)
        {
          default:
            rectwidth = rectheight = cellsize - lwidth - 2;
            break;
          case 1: // x direction
            rectwidth = (abs(GETX(lineend,sizex) - GETX(linestart,sizex)) + 1)*cellsize - lwidth - 2;
            rectheight = cellsize - lwidth - 2;
            break;
          case 2: // y direction
            rectwidth = cellsize - lwidth - 2;
            rectheight = (abs(GETY(lineend,sizex) - GETY(linestart,sizex)) + 1)*cellsize - lwidth - 2;
            break;
        }
        rectx = xcenter + GETX(rectstart,sizex)*cellsize + lwidth + 1;
        recty = ycenter + GETY(rectend,sizex)*cellsize + lwidth + 1;
        gfx.fillRect(rectx, recty, rectwidth, rectheight, EPD_RED);
        //Serial.println("draw line from " + COORD(linestart,sizex) + " to " + COORD(lineend,sizex));
        //Serial.println("rectangle @ " + COORD(rectstart,sizex) + ": " + String(rectwidth) + " by " + String(rectheight));
        linestart = lineend;
        //lastdir = dir;
        lastdir = getDirection(linestart,mazesolution[i+1]);
      }
      else
        i++;
    }
    // draw endline
    rectx = xcenter + GETX(mazesolution[solutioncount-1],sizex)*cellsize + lwidth + 1;
    recty = ycenter + GETY(mazesolution[solutioncount-1],sizex)*cellsize + lwidth + 1;
    rectwidth = cellsize - lwidth - 2;
    rectheight = cellsize ;
    gfx.fillRect(rectx, recty, rectwidth, rectheight, EPD_RED);
    //Serial.println("ending rectangle @ " + String(rectx) + "," + String(recty) + ": " + String(rectwidth) + " by " + String(rectheight));
  }
  gfx.display();
  Serial.println("display update completed");
  gfx.powerDown();
  neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
  neopixel.show();
}

/*
   print_block_maze() prints out the maze using the specified block
   character. This was the print routine for the original maze program.
   You can use it to print mazes to the terminal.
*/
void print_block_maze()
{
  int incrx, incry, incr2;
  char buff[5];
  for(incry=0; incry < sizey; incry++)
  {
    for(incr2=0; incr2 < 2; incr2++)
    {
      for(incrx=0; incrx < sizex; incrx++)
      {
        switch(incr2)
        {
        case 0:
          strcpy(buff,"  ");
          if(incry > 0)
          {
          if((*(maze+incry*sizex+incrx)&RIGHT)!=0)
            buff[1]=BLOCK_CHAR;
          }
          Serial.print(buff);
          break;
        case 1:
          strcpy(buff,"  ");
          if((*(maze+incry*sizex+incrx)&BOTTOM)!=0 && incrx > 0)
            buff[0]=BLOCK_CHAR;
          if(((incry < (sizey-1)) && 
            ((*(maze+(incry+1)*sizex+incrx)&RIGHT)!=0))||
            (buff[0]==BLOCK_CHAR)|| (incrx==0) ||
            ((*(maze+incry*sizex+incrx)&RIGHT)!=0) ||
            ((incrx < (sizex-1)) &&
            ((*(maze+incry*sizex+incrx+1)&&BOTTOM)!=0)))
            buff[1]=BLOCK_CHAR;
          Serial.print(buff);
          break;
        }
      }
      Serial.println();
    }
  }  
}

/*
   cell_join() joins two cells together, effectively breaking down a wall within
   the maze.
*/
void cell_join(int cell1, int cell2)
{
  int incr,val;
  
  val=*(mazepath+cell2);
  /* set mazepath value */
  //for(incr=0; incr < sizex*sizey; incr++)
  for(incr = sizex*sizey-1; incr >= 0; incr--)
    if(*(mazepath+incr)==val)
      *(mazepath+incr)=*(mazepath+cell1);
  /* set graphics */
  if(cell1+1 == cell2) /* open right wall */
    *(maze+cell1)=*(maze+cell1)&~RIGHT;
  else /* open bottom wall */
    *(maze+cell1)=*(maze+cell1)&~BOTTOM;
}

/*
   connect() attempts to connect two squares together, returning
   FALSE if the attempt failed
*/
int connect(int cell)
{
  int incr;
  int cellcheck[2]; /* adjacent cell attempts */
  /* check if cell is a border, if so, return false */
  if((cell < sizex) /* top line */
  ||((cell%sizex)==0)) /* left line */
    return(FALSE);
  /* determine order of cell attempts */
  cellcheck[0]=random(2);
  cellcheck[1]=(cellcheck[0]+1)%2;
  /* check cells to see if can be connected */
  for(incr=0; incr < 2; incr++)
  {
    if((GETX(cell,sizex)==(sizex-1))&&(cellcheck[incr]==0))
      continue; // do not attempt to open right edge of maze
    //if((cell > (sizex*(sizey-1)))&&(cellcheck[incr]==1))
    if((GETY(cell,sizex)==(sizey-1))&&(cellcheck[incr]==1))
      continue; // do not attempt to open bottom edge of maze
    if(*(mazepath+cell)!=*(mazepath+cell+1+cellcheck[incr]*(sizex-1)))
    {
      cell_join(cell,cell+1+cellcheck[incr]*(sizex-1));
      return(TRUE);
    }
  }
  return(FALSE);
}

/*
   generate() is the function that generates a random maze.  It calls connect()
   (which, in turn, calls cell_join()) to generate the maze.
*/
void generate()
{
  int cell,checkcell,incr,complete;
  do
  {
    complete=TRUE;
    /* pick a random cell */
    cell=sizex + random(sizex*(sizey-1));
    /* find the next cell that can be connected */
    for(incr=0; incr < sizex*sizey; incr++)
    {
      checkcell=(incr+cell)%(sizex*sizey);
      if((checkcell < sizex)||((checkcell%sizex)==0))
        continue;
      if(connect(checkcell))
      {
        complete=FALSE;
        break;
      }
    }
  }
  while(!complete);
  /* break walls for start and end of maze, near center */
  cell=sizex/4+(long)random(sizex/2);
  *(maze+cell)=*(maze+cell)&~BOTTOM;
  cell=sizex/4+(long)random(sizex/2)+sizex*(sizey-1);
  *(maze+cell)=*(maze+cell)&~BOTTOM;
}

/*
 * error() display error message and blink red neopixel
 */
void error(const char *err)
{
  Serial.println(err);
  while(1)
  {
    neopixel.setPixelColor(0, neopixel.Color(255, 0, 0));
    neopixel.show(); 
    delay(400);
    neopixel.setPixelColor(0, neopixel.Color(0, 0, 0));
    neopixel.show(); 
    delay(100);      
  }
}

void setup() {
  Serial.begin(115200);
  //while(!Serial);
  delay(1000);
  Serial.println(
    "XXXXXXX XXXXXXXXXXXXXXXXXXXXX\n"
    "X  Maze Generation Program  X\n"
    "X  Written by Dan Cogliano  X\n"
    "X  For Adafruit Industries  X\n"
    "XXXXXXXXXXXXXXXXXXXXX XXXXXXX\n\n");

  randomSeed(analogRead(0));

  neopixel.begin();
  neopixel.show();
  gfx.begin();
  Serial.println("ePaper display initialized");
  gfx.clearBuffer();
  gfx.setRotation(1);
  int w = gfx.width();
  int h = gfx.height();
  // assuming cell size of 5 pixels is the smallest supported maze
  if((maze=(char *)malloc((w/5) *  (h/5) * sizeof(char)))==NULL)
  {
    error("Not enough memory available for maze\n");
  }
  if((mazepath=(uint16_t *)malloc((w/5) *  (h)/5 * sizeof(uint16_t)))==NULL)
  {
    error("Not enough memory available for maze\n");
  }
  if((mazesolution=(uint16_t *)malloc((w/5) *  (h)/5 * sizeof(uint16_t)))==NULL)
  {
    error("Not enough memory available for maze\n");
  }
  
  init_maze(14,4);
  generate();
  //print_block_maze();
  print_epaper_maze();
}

/*
 * readButtons() to check if a button has been pressed
 */
int8_t readButtons(void) {
  uint16_t reading = analogRead(A3);
  //Serial.println(reading);

  if (reading > 600) {
    return 0; // no buttons pressed
  }
  if (reading > 400) {
    return 4; // button D pressed
  }
  if (reading > 250) {
    return 3; // button C pressed
  }
  if (reading > 125) {
    return 2; // button B pressed
  }
  return 1; // Button A pressed
}

void loop() {
  static bool showsolution = true;
  int button = readButtons();
  if (button == 0) {
    return;
  }
  Serial.print("Button "); Serial.print(button); Serial.println(" pressed");
  if (button == 1) {
    Serial.println("easy maze");
    init_maze(14,4);
    generate();
    //print_block_maze();
    print_epaper_maze();    
    showsolution = true;
  }

  if (button == 2) {
    Serial.println("medium maze");
    init_maze(10,3);
    generate();
    //print_block_maze();
    print_epaper_maze();    
    showsolution = true;
  }

  if (button == 3) {
    Serial.println("hard maze");
    init_maze(7,2);
    //init_maze(5,1); // smallest/hardest maze supported
    generate();
    //print_block_maze();
    print_epaper_maze();
    showsolution = true;
  }

  if (button == 4) {
    Serial.println("solve maze");
    solve();
    print_epaper_maze(showsolution);
    showsolution = !showsolution;
  }
}
