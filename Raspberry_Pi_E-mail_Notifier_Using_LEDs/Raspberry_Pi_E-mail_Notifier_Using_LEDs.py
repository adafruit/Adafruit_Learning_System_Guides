import time
import board
from imapclient import IMAPClient
from digitalio import DigitalInOut, Direction

HOSTNAME = 'imap.gmail.com'
MAILBOX = 'Inbox'
MAIL_CHECK_FREQ = 60        # check mail every 60 seconds

# The following three variables must be customized for this
# script to work
USERNAME = 'your username here'
PASSWORD = 'your password here'
NEWMAIL_OFFSET = 1          # my unread messages never goes to zero, use this to override

# setup Pi pins as output for LEDs
green_led = DigitalInOut(board.D18)
red_led = DigitalInOut(board.D23)
green_led.direction = Direction.OUTPUT
red_led.direction = Direction.OUTPUT

def mail_check():
    # login to mailserver
    server = IMAPClient(HOSTNAME, use_uid=True, ssl=True)
    server.login(USERNAME, PASSWORD)

    # select our MAILBOX and looked for unread messages
    unseen = server.folder_status(MAILBOX, ['UNSEEN'])

    # number of unread messages
    # print to console to determine NEWMAIL_OFFSET
    newmail_count = (unseen[b'UNSEEN'])
    print('%d unseen messages' % newmail_count)

    if newmail_count > NEWMAIL_OFFSET:
        green_led.value = True
        red_led.value = False
    else:
        green_led.value = False
        red_led.value = True

    time.sleep(MAIL_CHECK_FREQ)

while True:
    mail_check()
