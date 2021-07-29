"""
NextBus class -- handles NextBus server queries and infers
arrival times based on last-queried predictions and elapsed time.
"""

# pylint: disable=bare-except, too-many-instance-attributes, too-many-arguments

import re
import time

class NextBus():
    """ Class to handle NextBus prediction times for one route & stop.
    """

    def __init__(self, network, agency, route, stop, data=None,
                 max_predictions=3, minimum_time=300):
        """ Constructor expects a Requests-capable Network object,
            strings for transit agency, route, and stop ID, plus optional
            per-stop data as defined by an application (e.g. text
            description, but could be an object or tuple of data, or None,
            or whatever's needed by the app), limits for the maximum number
            of future arrivals to predict (limited to server response,
            typically 5) and minimum time below which arrivals are not shown
            (to discourage unsafe bus-chasing).
        """
        self.network = network
        self.agency = agency
        self.route = route
        self.stop = stop
        self.data = data
        self.max_predictions = max_predictions
        self.minimum_time = minimum_time
        self.predictions = []
        self.last_query_time = -1000

    def fetch(self):
        """ Contact NextBus server and request predictions for one
            agency/route/stop.
        """
        try:
            url = ('http://webservices.nextbus.com/service/publicXMLFeed?' +
                   'command=predictions&a=' + self.agency +
                   '&r=' + self.route + '&s=' + self.stop)
            response = self.network.requests.get(url)
            if response.status_code == 200:
                string = response.text
                self.last_query_time = time.monotonic()
                self.predictions = []
                while len(self.predictions) < self.max_predictions:
                    # CircuitPython version of re library doesn't have findall.
                    # Search for first instance of seconds="N" string and then
                    # increment the string position based on match length.
                    match = re.search('seconds=\"[0-9]*', string)
                    if match:
                        seconds = int(match.group(0)[9:]) # Remove 'seconds="'
                        if seconds >= self.minimum_time:
                            self.predictions.append(seconds)
                        string = string[match.end():]
                    else:
                        break
                self.predictions.sort()
        except:
            # If server query fails, we can keep extrapolating from the
            # last set of predictions and try query again on next pass.
            pass

    def predict(self):
        """ Extrapolate predictions based on last values queried from
            NextBus server and time elapsed since last query. Predictions
            are returned as a list of integer seconds values.
        """
        times = []
        for predict in self.predictions:
            seconds = predict - (time.monotonic() - self.last_query_time)
            if seconds >= self.minimum_time:
                times.append(seconds)
        return times
