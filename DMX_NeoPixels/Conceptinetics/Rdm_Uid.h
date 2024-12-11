/*
  Rdm_Uid.h - DMX library for Arduino with RDM (Remote Device Management) support
  Copyright (c) 2013 W.A. van der Meeren <danny@illogic.nl>.  All right reserved.

  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 3 of the License, or (at your option) any later version.

  This library is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
  Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public
  License along with this library; if not, write to the Free Software
  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
*/


#ifndef RDM_UID_H_
#define RDM_UID_H_

#include <inttypes.h>

//
//48 bit UID Representation to identify RDM transponders
//
struct RDM_Uid {

    void Initialize ( uint16_t m, uint8_t d1, uint8_t d2, uint8_t d3, uint8_t d4 ) 
    {
		m_id[0]  = ((uint8_t) (((uint16_t) (m)) >> 8));
        m_id[1]  = (uint8_t)m; 
		m_id[2]  = d1;
		m_id[3]  = d2;
		m_id[4]  = d3;
		m_id[5]  = d4;
	}

    void copy ( const RDM_Uid &orig ) 
    {
	    for ( uint8_t i = 0; i < 6; i++ )
            m_id[i] = orig.m_id[i];
    }

	bool operator == ( const RDM_Uid & orig ) const
	{
		for ( uint8_t i = 0; i < 6; i++ )
			if ( m_id[i] != orig.m_id[i] )
				return false;

        return true;
	}

	bool operator != ( const RDM_Uid & orig ) const
	{
		return !(*this == orig);
	}

	bool operator < ( const RDM_Uid & v ) const
	{
		for ( uint8_t i = 0; i < 6; i++ )
			if ( m_id[i] != v.m_id[i] )
				return ( m_id[i] < v.m_id[i] );
	}

	bool operator > ( const RDM_Uid & v ) 
    {
		for ( uint8_t i = 0; i < 6; i++ )
			if ( m_id[i] != v.m_id[i] )
				return ( m_id[i] > v.m_id[i] );
	}

    // 
    // match_mid = manufacturer id to match
    //
    bool isBroadcast ( uint8_t match_mid[2] )
    {
        // Check for genuine broadcast on device part
        for ( uint8_t i = 2; i < 6; i++ )
            if ( m_id[i] != 0xff )
                return false;

        // Broadcast or manufacturer designated broadcast
        if ( (m_id[0] == 0xff && m_id[1] == 0xff) ||
             (m_id[0] == match_mid[0] && m_id[1] == match_mid[1]) )
             return true;
        
        // No broadcast    
        return false;
    }

	uint8_t   m_id[6];     //16bit manufacturer id + 32 bits device id
};


#endif /* RDM_UID_H_ */
