import paho.mqtt.publish as publish
import time

AIO_USERNAME = 'YOURUSERNAMEHERE'
AIO_KEY = 'YOURKEYHERE'

AIO_TOPIC =       AIO_USERNAME + '/feeds/redlight'
AIO_YELLOWTOPIC = AIO_USERNAME + '/feeds/yellowlight'
AIO_GREENTOPIC =  AIO_USERNAME + '/feeds/greenlight'

def webhook_handler(event, context):
	print('Starting webhook handler!')
	action = event.get('action')
	print('Issue action: {0}'.format(action))
	auth = {'username': AIO_USERNAME, 'password': AIO_KEY}

	# for issues opened & closed
	if action == 'closed':
		publish.single(AIO_TOPIC, payload='OFF', hostname='io.adafruit.com', auth=auth)
	elif action in ('opened', 'reopened'):
		publish.single(AIO_TOPIC, payload='ON', hostname='io.adafruit.com', auth=auth)
	# starring & watching
	elif action == 'started':
		publish.single(AIO_YELLOWTOPIC, payload='ON', hostname='io.adafruit.com', auth=auth)
		time.sleep(1)
		publish.single(AIO_YELLOWTOPIC, payload='OFF', hostname='io.adafruit.com', auth=auth)
	# look for pushes
	elif "commits" in event:
		publish.single(AIO_GREENTOPIC, payload='ON', hostname='io.adafruit.com', auth=auth)
		time.sleep(1)
		publish.single(AIO_GREENTOPIC, payload='OFF', hostname='io.adafruit.com', auth=auth)

	return 'OK'


if __name__ == '__main__':
	webhook_handler({'action': 'started'}, {})
