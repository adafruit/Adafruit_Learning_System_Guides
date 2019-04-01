"""
LIFX Smart Lighting HTTP API Helper

Brent Rubell for Adafruit Industries, 2019
"""
# toss these into the init
LIFX_URL = 'https://api.lifx.com/v1/lights/'

class LIFX_API():
    """
    Interface for the LIFX HTTP Remote API
    """
    def __init__(self, wifi, lifx_token):
        """
        :param wifi_manager wifi: WiFiManager object from ESPSPI_WiFiManager or ESPAT_WiFiManager
        :param str lifx_token: LIFX Cloud API token (https://api.developer.lifx.com/docs/authentication)
        """
        self._wifi = wifi
        self._lifx_token = lifx_token
        self.auth_header = {"Authorization": "Bearer %s" % self._lifx_token,}


    def enumerate_lights():
        """Returns all lights associated with the LIFX Cloud Account
        """
        response = wifi.get(
            url=LIFX_URL+'all',
            headers=self._auth_header
        )
        resp = response.json()
        return resp
        response.close()

    def toggle_lights(selector, all=False, duration=0):
        """Toggles current state of LIFX bulb.
        :param dict selector: Selector to control which lights are requested.
        :param bool all: Toggle all lights at once. Defaults to false.
        :param double duration: Time (in seconds) to spend performing a toggle. Defaults to 0.
        """
        response = wifi.post(
            url=LIFX_URL+selector+'/toggle',
            headers = self._auth_header,
            json = {'duration':duration},
        )
        resp = response.json()
        return resp
        response.close()

    def set_light(selector, power=None, color=None, brightness=None, duration=None, fast_mode=False):
        """Sets the state of the lights within the selector.
        :param dict selector: Selector to control which lights are requested.
        :param str power: Sets the power state of the bulb (on/off).
        :param str color: Color to set the bulb to (https://api.developer.lifx.com/v1/docs/colors).
        :param double brightness: Brightness level of the bulb, from 0.0 to 1.0.
        :param double duration: How long (in seconds) you want the power action to take.
        :param bool fast: Executes fast mode, no initial state check or waiting for results.
        """
        response = wifi.put(
            url=LIFX_URL+selector+'/state',
            headers=self._auth_header,
            json={'power':"",
                    'color':color,
                    'brightness':brightness,
                    'duration':duration,
                    'fast':fast_mode
            }
        )
        resp = response.json()
        return resp
        response.close()