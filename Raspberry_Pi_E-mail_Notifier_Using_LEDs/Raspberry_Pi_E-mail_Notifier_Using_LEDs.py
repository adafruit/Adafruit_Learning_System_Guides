import time
from imapclient import IMAPClient
from digitalio import DigitalInOut, Direction

#DEBUG = True

HOSTNAME = 'imap.gmail.com'
USERNAME = 'your username here'
PASSWORD = 'your password here'
MAILBOX = 'Inbox'

NEWMAIL_OFFSET = 1   # my unread messages never goes to zero, yours might
MAIL_CHECK_FREQ = 60 # check mail every 60 seconds

# setup Pi pins as output for LEDs
green_led = DigitalInOut(board.D18)
red_led = DigitalInOut(board.D23)
green_led.direction = Direction.OUTPUT
red_led = Direction.OUTPUT

def loop():
    server = IMAPClient(HOSTNAME, use_uid=True, ssl=True)
    server.login(USERNAME, PASSWORD)

    if DEBUG:
        print('Logging in as ' + USERNAME)
        select_info = server.select_folder(MAILBOX)
        print('%d messages in INBOX' % select_info['EXISTS'])

    folder_status = server.folder_status(MAILBOX, 'UNSEEN')
    newmails = int(folder_status['UNSEEN'])

    if DEBUG:
        print "You have", newmails, "new emails!"

    if newmails > NEWMAIL_OFFSET:
        green_led.value = True
        red_led.value = False
    else:
        green_led.value = False
        red_led.value = True

    time.sleep(MAIL_CHECK_FREQ)

if __name__ == '__main__':
    try:
        print 'Press Ctrl-C to quit.'
        while True:
            loop()
