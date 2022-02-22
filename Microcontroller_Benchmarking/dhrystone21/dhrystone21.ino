// SPDX-FileCopyrightText: 1988 Reinhold P. Weicker
// SPDX-FileCopyrightText: Gareth Halfacree
// SPDX-FileCopyrightText: Ken Boak
// SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT


/* Dhrystone benchmark, modified for use with Arduinos and compatibles.
 * Based on work by Ken Boak.
 * Further modified to allow execution on an ATmega328-based board.
 * Modified by Gareth Halfacree <gareth@halfacree.co.uk>
 */

/*
 *************************************************************************
 *
 *                   "DHRYSTONE" Benchmark Program
 *                   -----------------------------
 *
 *  Version:    C, Version 2.1
 *
 *  File:       dhry_1.c (part 2 of 3)
 *
 *  Date:       May 25, 1988
 *
 *  Author:     Reinhold P. Weicker
 *
 *************************************************************************
 */

#include "dhry.h"


/* Global Variables: */

Rec_Pointer     Ptr_Glob,
                Next_Ptr_Glob;
int             Int_Glob;
Boolean         Bool_Glob;
char            Ch_1_Glob,
                Ch_2_Glob;
int             Arr_1_Glob [25];        /* <-- changed from 50 */
int             Arr_2_Glob [25] [25];   /* <-- changed from 50 */

char Reg_Define[] = "Register option selected.";

#ifndef ROPT
#define REG
        /* REG becomes defined as empty */
        /* i.e. no register variables   */
#else
#define REG register
#endif


/* variables for time measurement: */

#define Too_Small_Time 2000000
                /* Measurements should last at least 2 seconds */

uint32_t      Begin_Time,
              End_Time,
              User_Time;

double        Microseconds,
              Dhrystones_Per_Second,
              Vax_Mips;

/* end of variables for time measurement */

void Proc_1( REG Rec_Pointer Ptr_Val_Par );
void Proc_2( One_Fifty * Int_Par_Ref );
void Proc_3( Rec_Pointer * Ptr_Ref_Par );
void Proc_4( void );
void Proc_5( void );

  /* main program, corresponds to procedures        */
  /* Main and Proc_0 in the Ada version             */
void setup() {

        One_Fifty       Int_1_Loc;
  REG   One_Fifty       Int_2_Loc;
        One_Fifty       Int_3_Loc;
  REG   char            Ch_Index;
        Enumeration     Enum_Loc;
        Str_30          Str_1_Loc;
        Str_30          Str_2_Loc;
  REG   long             Run_Index;
  REG   long             Number_Of_Runs;

  /* Initializations */

  Serial.begin(115200); 
  while (!Serial) {
    delay(10); // wait for serial port to connect
  }
  Serial.println(F("Dhrystone Benchmark, Version 2.1 (Language: C)"));

  Next_Ptr_Glob = (Rec_Pointer)malloc (sizeof (Rec_Type));
  Ptr_Glob = (Rec_Pointer)malloc (sizeof (Rec_Type));

  Ptr_Glob->Ptr_Comp                    = Next_Ptr_Glob;
  Ptr_Glob->Discr                       = Ident_1;
  Ptr_Glob->variant.var_1.Enum_Comp     = Ident_3;
  Ptr_Glob->variant.var_1.Int_Comp      = 40;
  strcpy (Ptr_Glob->variant.var_1.Str_Comp, 
          "DHRYSTONE PROGRAM, SOME STRING");
  strcpy (Str_1_Loc, "DHRYSTONE PROGRAM, 1'ST STRING");

  Arr_2_Glob [8][7] = 10;
        /* Was missing in published program. Without this statement,    */
        /* Arr_2_Glob [8][7] would have an undefined value.             */
        /* Warning: With 16-Bit processors and Number_Of_Runs > 32000,  */
        /* overflow may occur for this array element.                   */

  Number_Of_Runs = 1000000;
  
  Serial.print(F("Execution starts, "));
  Serial.print(Number_Of_Runs);
  Serial.println(F(" runs through Dhrystone"));
  Serial.println();
  
  /***************/
  /* Start timer */
  /***************/
 
  Begin_Time = micros();

  for (Run_Index = 1; Run_Index <= Number_Of_Runs; ++Run_Index)
  {
    Proc_5();
    Proc_4();
      /* Ch_1_Glob == 'A', Ch_2_Glob == 'B', Bool_Glob == true */
    Int_1_Loc = 2;
    Int_2_Loc = 3;
    strcpy (Str_2_Loc, "DHRYSTONE PROGRAM, 2'ND STRING");
    Enum_Loc = Ident_2;
    Bool_Glob = ! Func_2 (Str_1_Loc, Str_2_Loc);
      /* Bool_Glob == 1 */
    while (Int_1_Loc < Int_2_Loc)  /* loop body executed once */
    {
      Int_3_Loc = 5 * Int_1_Loc - Int_2_Loc;
        /* Int_3_Loc == 7 */
      Proc_7 (Int_1_Loc, Int_2_Loc, &Int_3_Loc);
        /* Int_3_Loc == 7 */
      Int_1_Loc += 1;
    } /* while */
      /* Int_1_Loc == 3, Int_2_Loc == 3, Int_3_Loc == 7 */
    Proc_8 (Arr_1_Glob, Arr_2_Glob, Int_1_Loc, Int_3_Loc);
      /* Int_Glob == 5 */
    Proc_1 (Ptr_Glob);
    for (Ch_Index = 'A'; Ch_Index <= Ch_2_Glob; ++Ch_Index)
                             /* loop body executed twice */
    {
      if (Enum_Loc == Func_1 (Ch_Index, 'C'))
          /* then, not executed */
        {
        Proc_6 (Ident_1, &Enum_Loc);
        strcpy (Str_2_Loc, "DHRYSTONE PROGRAM, 3'RD STRING");
        Int_2_Loc = Run_Index;
        Int_Glob = Run_Index;
        }
    }
      /* Int_1_Loc == 3, Int_2_Loc == 3, Int_3_Loc == 7 */
    Int_2_Loc = Int_2_Loc * Int_1_Loc;
    Int_1_Loc = Int_2_Loc / Int_3_Loc;
    Int_2_Loc = 7 * (Int_2_Loc - Int_3_Loc) - Int_1_Loc;
      /* Int_1_Loc == 1, Int_2_Loc == 13, Int_3_Loc == 7 */
    Proc_2 (&Int_1_Loc);
      /* Int_1_Loc == 5 */

  } /* loop "for Run_Index" */

  /**************/
  /* Stop timer */
  /**************/

  End_Time = micros();
  User_Time = End_Time - Begin_Time;

  Serial.println(F("Execution ends"));
/*
  printf ("\r\n");
  printf ("Final values of the variables used in the benchmark:\r\n");
  printf ("\r\n");
  printf ("Int_Glob:            %d\r\n", Int_Glob);
  printf ("        should be:   %d\r\n", 5);
  printf ("Bool_Glob:           %d\r\n", Bool_Glob);
  printf ("        should be:   %d\r\n", 1);
  printf ("Ch_1_Glob:           %c\r\n", Ch_1_Glob);
  printf ("        should be:   %c\r\n", 'A');
  printf ("Ch_2_Glob:           %c\r\n", Ch_2_Glob);
  printf ("        should be:   %c\r\n", 'B');
  printf ("Arr_1_Glob[8]:       %d\r\n", Arr_1_Glob[8]);
  printf ("        should be:   %d\r\n", 7);
  printf ("Arr_2_Glob[8][7]:    %d\r\n", Arr_2_Glob[8][7]);
  printf ("        should be:   Number_Of_Runs + 10\r\n");
  printf ("Ptr_Glob->\r\n");
  printf ("  Ptr_Comp:          %d\r\n", (int) Ptr_Glob->Ptr_Comp);
  printf ("        should be:   (implementation-dependent)\r\n");
  printf ("  Discr:             %d\r\n", Ptr_Glob->Discr);
  printf ("        should be:   %d\r\n", 0);
  printf ("  Enum_Comp:         %d\r\n", Ptr_Glob->variant.var_1.Enum_Comp);
  printf ("        should be:   %d\r\n", 2);
  printf ("  Int_Comp:          %d\r\n", Ptr_Glob->variant.var_1.Int_Comp);
  printf ("        should be:   %d\r\n", 17);
  printf ("  Str_Comp:          %s\r\n", Ptr_Glob->variant.var_1.Str_Comp);
  printf ("        should be:   DHRYSTONE PROGRAM, SOME STRING\r\n");
  printf ("Next_Ptr_Glob->\r\n");
  printf ("  Ptr_Comp:          %d\r\n", (int) Next_Ptr_Glob->Ptr_Comp);
  printf ("        should be:   (implementation-dependent), same as above\r\n");
  printf ("  Discr:             %d\r\n", Next_Ptr_Glob->Discr);
  printf ("        should be:   %d\r\n", 0);
  printf ("  Enum_Comp:         %d\r\n", Next_Ptr_Glob->variant.var_1.Enum_Comp);
  printf ("        should be:   %d\r\n", 1);
  printf ("  Int_Comp:          %d\r\n", Next_Ptr_Glob->variant.var_1.Int_Comp);
  printf ("        should be:   %d\r\n", 18);
  printf ("  Str_Comp:          %s\r\n", Next_Ptr_Glob->variant.var_1.Str_Comp);
  printf ("        should be:   DHRYSTONE PROGRAM, SOME STRING\r\n");
  printf ("Int_1_Loc:           %d\r\n", Int_1_Loc);
  printf ("        should be:   %d\r\n", 5);
  printf ("Int_2_Loc:           %d\r\n", Int_2_Loc);
  printf ("        should be:   %d\r\n", 13);
  printf ("Int_3_Loc:           %d\r\n", Int_3_Loc);
  printf ("        should be:   %d\r\n", 7);
  printf ("Enum_Loc:            %d\r\n", Enum_Loc);
  printf ("        should be:   %d\r\n", 1);
  printf ("Str_1_Loc:           %s\r\n", Str_1_Loc);
  printf ("        should be:   DHRYSTONE PROGRAM, 1'ST STRING\r\n");
  printf ("Str_2_Loc:           %s\r\n", Str_2_Loc);
  printf ("        should be:   DHRYSTONE PROGRAM, 2'ND STRING\r\n");
  printf ("\r\n");
*/

  if (User_Time < Too_Small_Time)
  {
    Serial.println(F("Measured time too small to obtain meaningful results"));
    Serial.println(F("Please increase number of runs"));
    Serial.println();
  }
  else
  {
    Microseconds = (double) User_Time / (double) Number_Of_Runs;
    Dhrystones_Per_Second = (double) Number_Of_Runs / ((double)User_Time/1000000.0);
    Vax_Mips = Dhrystones_Per_Second / 1757.0;
  }
/*
#ifdef ROPT
    printf ("Register option selected?  YES\r\n");
#else
    printf ("Register option selected?  NO\r\n");
    strcpy(Reg_Define, "Register option not selected.");
#endif
*/
    Serial.print(F("Microseconds for one run through Dhrystone: "));
    Serial.println(Microseconds);
    Serial.print(F("Dhrystones per Second: "));
    Serial.println(Dhrystones_Per_Second);
    Serial.print(F("VAX MIPS rating = "));
    Serial.println(Vax_Mips);
  //}
}

void loop() {  
}

void Proc_1( REG Rec_Pointer Ptr_Val_Par )
/******************/
    /* executed once */
{
  REG Rec_Pointer Next_Record = Ptr_Val_Par->Ptr_Comp;  
                                        /* == Ptr_Glob_Next */
  /* Local variable, initialized with Ptr_Val_Par->Ptr_Comp,    */
  /* corresponds to "rename" in Ada, "with" in Pascal           */
  
  structassign (*Ptr_Val_Par->Ptr_Comp, *Ptr_Glob);
  Ptr_Val_Par->variant.var_1.Int_Comp = 5;
  Next_Record->variant.var_1.Int_Comp 
        = Ptr_Val_Par->variant.var_1.Int_Comp;
  Next_Record->Ptr_Comp = Ptr_Val_Par->Ptr_Comp;
  Proc_3 (&Next_Record->Ptr_Comp);
    /* Ptr_Val_Par->Ptr_Comp->Ptr_Comp 
                        == Ptr_Glob->Ptr_Comp */
  if (Next_Record->Discr == Ident_1)
    /* then, executed */
  {
    Next_Record->variant.var_1.Int_Comp = 6;
    Proc_6 (Ptr_Val_Par->variant.var_1.Enum_Comp, 
           &Next_Record->variant.var_1.Enum_Comp);
    Next_Record->Ptr_Comp = Ptr_Glob->Ptr_Comp;
    Proc_7 (Next_Record->variant.var_1.Int_Comp, 10, 
           &Next_Record->variant.var_1.Int_Comp);
  }
  else /* not executed */
    structassign (*Ptr_Val_Par, *Ptr_Val_Par->Ptr_Comp);
} /* Proc_1 */


void Proc_2( One_Fifty * Int_Par_Ref )
/******************/
    /* executed once */
    /* *Int_Par_Ref == 1, becomes 4 */
{
  One_Fifty  Int_Loc;
  Enumeration   Enum_Loc;

  Int_Loc = *Int_Par_Ref + 10;
  do /* executed once */
    if (Ch_1_Glob == 'A')
      /* then, executed */
    {
      Int_Loc -= 1;
      *Int_Par_Ref = Int_Loc - Int_Glob;
      Enum_Loc = Ident_1;
    } /* if */
  while (Enum_Loc != Ident_1); /* true */
} /* Proc_2 */


void Proc_3( Rec_Pointer * Ptr_Ref_Par )
/******************/
    /* executed once */
    /* Ptr_Ref_Par becomes Ptr_Glob */
{
  if (Ptr_Glob != Null)
    /* then, executed */
    *Ptr_Ref_Par = Ptr_Glob->Ptr_Comp;
  Proc_7 (10, Int_Glob, &Ptr_Glob->variant.var_1.Int_Comp);
} /* Proc_3 */


void Proc_4( void ) /* without parameters */
/*******/
    /* executed once */
{
  Boolean Bool_Loc;

  Bool_Loc = Ch_1_Glob == 'A';
  Bool_Glob = Bool_Loc | Bool_Glob;
  Ch_2_Glob = 'B';
} /* Proc_4 */


void Proc_5( void ) /* without parameters */
/*******/
    /* executed once */
{
  Ch_1_Glob = 'A';
  Bool_Glob = false;
} /* Proc_5 */


        /* Procedure for the assignment of structures,          */
        /* if the C compiler doesn't support this feature       */
#ifdef  NOSTRUCTASSIGN
memcpy (d, s, l)
register char   *d;
register char   *s;
register int    l;
{
        while (l--) *d++ = *s++;
}
#endif

/*
 *************************************************************************
 *
 *                   "DHRYSTONE" Benchmark Program
 *                   -----------------------------
 *
 *  Version:    C, Version 2.1
 *
 *  File:       dhry_2.c (part 3 of 3)
 *
 *  Date:       May 25, 1988
 *
 *  Author:     Reinhold P. Weicker
 *
 *************************************************************************
 */


Boolean Func_3( Enumeration Enum_Par_Val );

void Proc_6( Enumeration Enum_Val_Par, Enumeration * Enum_Ref_Par )
/*********************************/
    /* executed once */
    /* Enum_Val_Par == Ident_3, Enum_Ref_Par becomes Ident_2 */
{
  *Enum_Ref_Par = Enum_Val_Par;
  if (! Func_3 (Enum_Val_Par))
    /* then, not executed */
    *Enum_Ref_Par = Ident_4;
  switch (Enum_Val_Par)
  {
    case Ident_1: 
      *Enum_Ref_Par = Ident_1;
      break;
    case Ident_2: 
      if (Int_Glob > 100)
        /* then */
      *Enum_Ref_Par = Ident_1;
      else *Enum_Ref_Par = Ident_4;
      break;
    case Ident_3: /* executed */
      *Enum_Ref_Par = Ident_2;
      break;
    case Ident_4: break;
    case Ident_5: 
      *Enum_Ref_Par = Ident_3;
      break;
  } /* switch */
} /* Proc_6 */


void Proc_7( One_Fifty Int_1_Par_Val, One_Fifty Int_2_Par_Val,
                                                       One_Fifty * Int_Par_Ref )
/**********************************************/
    /* executed three times                                      */
    /* first call:      Int_1_Par_Val == 2, Int_2_Par_Val == 3,  */
    /*                  Int_Par_Ref becomes 7                    */
    /* second call:     Int_1_Par_Val == 10, Int_2_Par_Val == 5, */
    /*                  Int_Par_Ref becomes 17                   */
    /* third call:      Int_1_Par_Val == 6, Int_2_Par_Val == 10, */
    /*                  Int_Par_Ref becomes 18                   */
{
  One_Fifty Int_Loc;

  Int_Loc = Int_1_Par_Val + 2;
  *Int_Par_Ref = Int_2_Par_Val + Int_Loc;
} /* Proc_7 */


void Proc_8( Arr_1_Dim Arr_1_Par_Ref, Arr_2_Dim Arr_2_Par_Ref,
                                          int Int_1_Par_Val, int Int_2_Par_Val )
/*********************************************************************/
    /* executed once      */
    /* Int_Par_Val_1 == 3 */
    /* Int_Par_Val_2 == 7 */
{
  REG One_Fifty Int_Index;
  REG One_Fifty Int_Loc;

  Int_Loc = Int_1_Par_Val + 5;
  Arr_1_Par_Ref [Int_Loc] = Int_2_Par_Val;
  Arr_1_Par_Ref [Int_Loc+1] = Arr_1_Par_Ref [Int_Loc];
  Arr_1_Par_Ref [Int_Loc+15] = Int_Loc;
  for (Int_Index = Int_Loc; Int_Index <= Int_Loc+1; ++Int_Index)
    Arr_2_Par_Ref [Int_Loc] [Int_Index] = Int_Loc;
  Arr_2_Par_Ref [Int_Loc] [Int_Loc-1] += 1;
  Arr_2_Par_Ref [Int_Loc+10] [Int_Loc] = Arr_1_Par_Ref [Int_Loc];
  Int_Glob = 5;
} /* Proc_8 */


Enumeration Func_1 ( Capital_Letter Ch_1_Par_Val, Capital_Letter Ch_2_Par_Val )
/*************************************************/
    /* executed three times                                         */
    /* first call:      Ch_1_Par_Val == 'H', Ch_2_Par_Val == 'R'    */
    /* second call:     Ch_1_Par_Val == 'A', Ch_2_Par_Val == 'C'    */
    /* third call:      Ch_1_Par_Val == 'B', Ch_2_Par_Val == 'C'    */
{
  Capital_Letter        Ch_1_Loc;
  Capital_Letter        Ch_2_Loc;

  Ch_1_Loc = Ch_1_Par_Val;
  Ch_2_Loc = Ch_1_Loc;
  if (Ch_2_Loc != Ch_2_Par_Val)
    /* then, executed */
    return (Ident_1);
  else  /* not executed */
  {
    Ch_1_Glob = Ch_1_Loc;
    return (Ident_2);
   }
} /* Func_1 */


Boolean Func_2( Str_30 Str_1_Par_Ref, Str_30 Str_2_Par_Ref )
/*************************************************/
    /* executed once */
    /* Str_1_Par_Ref == "DHRYSTONE PROGRAM, 1'ST STRING" */
    /* Str_2_Par_Ref == "DHRYSTONE PROGRAM, 2'ND STRING" */
{
  REG One_Thirty        Int_Loc;
      Capital_Letter    Ch_Loc;

  Int_Loc = 2;
  while (Int_Loc <= 2) /* loop body executed once */
    if (Func_1 (Str_1_Par_Ref[Int_Loc],
                Str_2_Par_Ref[Int_Loc+1]) == Ident_1)
      /* then, executed */
    {
      Ch_Loc = 'A';
      Int_Loc += 1;
    } /* if, while */
  if (Ch_Loc >= 'W' && Ch_Loc < 'Z')
    /* then, not executed */
    Int_Loc = 7;
  if (Ch_Loc == 'R')
    /* then, not executed */
    return (true);
  else /* executed */
  {
    if (strcmp (Str_1_Par_Ref, Str_2_Par_Ref) > 0)
      /* then, not executed */
    {
      Int_Loc += 7;
      Int_Glob = Int_Loc;
      return (true);
    }
    else /* executed */
      return (false);
  } /* if Ch_Loc */
} /* Func_2 */


Boolean Func_3( Enumeration Enum_Par_Val )
/***************************/
    /* executed once        */
    /* Enum_Par_Val == Ident_3 */
{
  Enumeration Enum_Loc;

  Enum_Loc = Enum_Par_Val;
  if (Enum_Loc == Ident_3)
    /* then, executed */
    return (true);
  else /* not executed */
    return (false);
} /* Func_3 */

