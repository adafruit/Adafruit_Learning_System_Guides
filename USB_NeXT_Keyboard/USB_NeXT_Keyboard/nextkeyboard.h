#include "wsksymdef.h"

/*	$NetBSD: wskbdmap_next.c,v 1.5 2008/04/28 20:23:30 martin Exp $	*/

/*-
 * Copyright (c) 1997 The NetBSD Foundation, Inc.
 * All rights reserved.
 *
 * This code is derived from software contributed to The NetBSD Foundation
 * by Juergen Hannken-Illjes.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE NETBSD FOUNDATION, INC. AND CONTRIBUTORS
 * ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
 * TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE FOUNDATION OR CONTRIBUTORS
 * BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */
 
#define KC(n) n

typedef unsigned short keysym_t;

static const keysym_t nextkbd_keydesc_us[] = {
/*  pos      normal		shifted */
    KC(3), 			KS_backslash,	KS_bar,
    KC(4), 			KS_bracketright, KS_braceright,
    KC(5), 			KS_bracketleft,	KS_braceleft,
    KC(6),                      KS_i, 0,
    KC(7),                      KS_o, 0,
    KC(8),                      KS_p, 0,
    KC(9),			KS_Left, 0,
    KC(11), 			KS_KP_0, 0,
    KC(12), 			KS_KP_Decimal, 0,
    KC(13),			KS_KP_Enter, 0,
    KC(15),			KS_Down, 0,
    KC(16),			KS_Right, 0,
    KC(17), 			KS_KP_1, 0,
    KC(18), 			KS_KP_4, 0,
    KC(19), 			KS_KP_6, 0,
    KC(20), 			KS_KP_3, 0,
    KC(21), 			KS_KP_Add, 0,
    KC(22),			KS_Up, 0,
    KC(23), 			KS_KP_2, 0,
    KC(24), 			KS_KP_5, 0,
    KC(27), 			KS_BackSpace, 0,
    KC(28), 			KS_equal,	KS_plus,
    KC(29), 			KS_minus,	KS_underscore,
    KC(30),  			KS_8,		KS_asterisk,
    KC(31), 			KS_9,		KS_parenleft,
    KC(32), 			KS_0,		KS_parenright,
    KC(33), 			KS_KP_7, 0,
    KC(34), 			KS_KP_8, 0,
    KC(35), 			KS_KP_9, 0,
    KC(36), 			KS_KP_Subtract, 0,
    KC(37), 			KS_KP_Multiply, 0,
    KC(38), 			KS_grave,	KS_asciitilde,
    KC(39), 			KS_KP_Equal, KS_bar,
    KC(40),			KS_KP_Divide, KS_backslash,
    KC(42), 			KS_Return, 0,
    KC(43), 			KS_apostrophe,	KS_quotedbl,
    KC(44), 			KS_semicolon,	KS_colon,
    KC(45), 			KS_l, 0,
    KC(46), 			KS_comma,	KS_less,
    KC(47), 			KS_period,	KS_greater,
    KC(48), 			KS_slash,	KS_question,
    KC(49),                     KS_z, 0,
    KC(50),                     KS_x, 0,
    KC(51),                     KS_c, 0,
    KC(52),                     KS_v, 0,
    KC(53),                     KS_b, 0,
    KC(54),                     KS_m, 0,
    KC(55),                     KS_n, 0,
    KC(56), 			KS_space, 0,
    KC(57),                     KS_a, 0,
    KC(58),                     KS_s, 0,
    KC(59),                     KS_d, 0,
    KC(60),                     KS_f, 0,
    KC(61),                     KS_g, 0,
    KC(62),                     KS_k, 0,
    KC(63),                     KS_j, 0,
    KC(64),                     KS_h, 0,
    KC(65), 			KS_Tab, 0,
    KC(66),                     KS_q, 0,
    KC(67),                     KS_w, 0,
    KC(68),                     KS_e, 0,
    KC(69),                     KS_r, 0,
    KC(70),                     KS_u, 0,
    KC(71),                     KS_y, 0,
    KC(72),                     KS_t, 0,
    KC(73),            	        KS_Escape, 0,
    KC(74),  			KS_1,		KS_exclam,
    KC(75),  			KS_2,		KS_at,
    KC(76),  			KS_3,		KS_numbersign,
    KC(77),  			KS_4,		KS_dollar,
    KC(78),  			KS_7,		KS_ampersand,
    KC(79),  			KS_6,		KS_asciicircum,
    KC(80),  			KS_5,		KS_percent,

    KC(90), 			KS_Shift_L, 0,
    KC(91), 			KS_Shift_R, 0,
    KC(92),   			KS_Alt_L, 0,
    KC(93),  			KS_Alt_R, 0,
    KC(94),			KS_Control_L, 0,
    KC(95), 			KS_Cmd1, 0,
    KC(96), 			KS_Cmd2, 0,

// special exception for volume up, down + brightness up, down
    KC(26),  	KS_AudioLower, 0,  // vol up
    KC(2),      KS_AudioRaise, 0,  // vol down
    KC(25),  	KS_Cmd_BrightnessUp, 0,  // bright up
    KC(1),      KS_Cmd_BrightnessDown, 0,  // bright down

};
