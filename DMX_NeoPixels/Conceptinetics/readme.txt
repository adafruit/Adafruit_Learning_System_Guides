
This library has been developed to support the CTC-DRA-13-R2 Isolated DMX-RDM Shield and CTC-DRA-10-1, CTC-DRA-10-R2 Shield on the Arduino platform. 
However, the use of this library is not limited to the prior mentioned boards. This library works on the principle of using a RS485 driver to drive a DMX line or act as a receiver ( DMX Slave )

If you wish to make additions or find bugs or would like to contribute in any other way then please don't hesitate to contact me via my email address: danny@illogic.nl or use report issues on the Sourceforge project page instead.


For information on installing libraries, see: http://arduino.cc/en/Guide/Libraries


*** COPYRIGHT STATEMENT ***

Copyright (c) 2017 W.A. van der Meeren <danny@illogic.nl>.  All right reserved.

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

CHANGE LOG:

	- 28-Feb-2017: Fixed various RDM timing issues
	- 28-Feb-2017: Removed unwanted transmission during line turnaround (RDM)
	- 28-Feb-2017: Updated break time to 176us to comply specs
	- 11-Oct-2016: Fix in setting range of channels, end channel does get set 
				   now as well to desired value
	- 23-Apr-2014: Fix to overide possible incorrect USART setting (rdm-alpha)
	- 17-Apr-2014: RDM responder issue solved in rdm-alpha
    - 24-jun-2013: Add on receive complete callback to original library as well
    - 14-jun-2013: Add on receive complete callback to dmx_slave in rdm-alpha library
    - 26-apr-2013: Add basic Remote Device Management support (alpha)
    - 14-apr-2013: Fixed startbyte recognition
    - 03-apr-2013: Fixed memomry allocation in slave
