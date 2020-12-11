""" Produce class -- handles server queries and generates seasonal produce
    lists for a time and place. See notes at end of file regarding data
    format and some design decisions.
"""

# pylint: disable=too-many-nested-blocks, pointless-string-statement

import json

class Produce():
    """ Class to generate seasonal produce lists from server-based JSON data.
    """

    def __init__(self, url, location):
        """ Constructor
        """
        self.url = url
        self.location = location
        self.geo = None
        self.produce = None


    def fetch(self, magtag=None):
        """ Retrieves current seasonal produce data from server,
            does some deserializing and processing for later filtering.
            This is currently tied to a MagTag object -- would prefer
            to function with more general WiFi-type object in the future
            so this could work on other boards.
        """
        if self.url.startswith('file:'):
            # JSON data is in local file (network value is ignored)
            with open(self.url[6:]) as jsonfile: # Skip initial 'file:/'
                json_data = json.load(jsonfile)
        else:
            # JSON data is on remote server
            response = magtag.network.fetch(self.url)
            if response.status_code == 200:
                json_data = response.json()

        # Convert JSON geo data into hierarchical string list for later:
        self.geo = self.geo_ring(json_data['geo'], self.location)

        # Produce data is simply JSON-deserialized for later:
        self.produce = json_data['produce']


    def geo_ring(self, geo_dict, name):
        """ Given a dict comprising hierarchical geographic identifiers,
            and a most-geographically-local name to match, return a list of
            'concentric' geo identifier strings sorted nearest to widest.
            Typically called in JSON fetch above (not by user code), based
            on requested location.
        """
        for key in list(geo_dict.keys()):      # For each key in dict...
            if key == name:                    # If it matches target name,
                return [key]                   # done, end search, return it
            for item in geo_dict[key]:         # Each item in value (list)...
                if isinstance(item, str):      # If it's a string,
                    if item == name:           # and matches our target name
                        return [item] + [key]  # done, return it w/parent
                elif isinstance(item, dict):   # Or, if it's a sub-dict...
                    sub = self.geo_ring(item, name) # Recursively scan down
                    if sub:                    # If item found in lower level
                        return sub + [key]     # Return list w key apended
        return None                            # No match


    def in_season(self, month):
        """ With JSON produce data previously loaded and geographic location
            previously set, and given a month number (1-12), return a
            list-of-strings of in-season produce for that time and place.
        """
        veg_list = []                              # No matches to start
        for veg_name in list(self.produce.keys()): # For each key ('Beets'),
            veg_obj = self.produce[veg_name]       # value is sub-dict
            for geo in self.geo:                   # Expanding geography
                try:
                    veg_months = veg_obj[geo]      # Local veg data, if any
                    # Months are evaluated in pairs, as season (start, end)
                    for first in range(0, len(veg_months), 2):
                        last = first + 1
                        # Sometimes the season wraps around the year end...
                        if veg_months[last] < veg_months[first]:
                            if not veg_months[last] < month < veg_months[first]:
                                veg_list.append(veg_name) # A match!
                        # Otherwise, normal month-range compare...
                        elif veg_months[first] <= month <= veg_months[last]:
                            veg_list.append(veg_name)     # A match!
                    break                          # Narrowest geo match, done
                except KeyError:                   # No veg data for geo key,
                    pass                           # try next widest geo ring
        veg_list.sort()                            # Alphabetize list
        return veg_list                            # Return alphabetized list


""" NOTES

Produce data is in a JSON file -- this could be fetched remotely by the
application of stored in a local file. Remote storage (e.g. Github) allows
data updates without installing new code, and allows others to contribute
changes. JSON isn't an ideal format for hand editing, and this code does
some uncouth things with the JSON format, but there's a desire to leverage
robust JSON parsing already available to CircuitPython, and to lessen the
file size and in-memory representation.

The JSON file contains two sections, with the keys "geo" and "produce".
Both must be present. The "geo" section hierarchically organizes geography
so the code can try using very location-specific data for a food before
working its way up to progressively wider (but maybe less useful) regions.
"produce" contains food names and geographic and seasonal data for each.

The initial dataset was derived from Farmers' Almanac, which provides seven
geographic regions for the continental United States, and four seasons.
No data is present for AK, HI, U.S. territories or other countries, nor
temporal resolution exceeding the provided 3-month periods -- hence the
mention of data updates and user contributions: the dataset will likely
evolve over time.

The original seven regions, and abbreviations used in the JSON, include:
1. Northeast & New England ("US-NE" in JSON)
2. Great Lakes, Ohio Valley, Midwest ("US-MW")
3. Southeast ("US-SE")
4. North Central ("US-NC")
5. South Central ("US-SC")
6. Northwest ("US-NW")
7. Southwest ("US-SW")

In the "geo" section of the JSON, there's initially a "US" dictionary key,
and the associated value is a list of sub-objects, each one's key is one of
the regions above, and values in turn are a list of state names (using 2-
letter postal codes) within that region...so that users can specify their
location by their familiar state code and not have to look up their
corresponding region. It's possible use further hierarchical subdivisions
(e.g. if a state is only a marginal match for a region, or for microclimates
within the same state), but this is not used in the initial dataset.
"geo" could've been a list of objects, and that's probably more JSON-like,
but instead is a single object and all keys are evaluated. It was more
compact this way. RAM is more precious than CPU cycles for this code, which
might only run once per day.)
The geo data is strictly hierarchical or "concentric" -- there's no support
for disjointed areas or crossing multiple regions (though "holes" are
possible) -- fully handling all that would get into complicated spatial
database stuff, and this is just a JSON hack, but adequate for the task.

In the "produce" section, each foodstuff name is a dictionary key (again,
rather than a list or "name": elements, every key is scanned, unusual but it
makes for small JSON). Each associated value is another JSON object (dict),
and the keys there represent geographic areas (using the same abbreviations
defined in the "geo" section) where it's grown. Multiple areas can be
specified, and the code's able to use the user's geo hierarchy to return the
"most local" data to display, falling back on progressively broader regions
if needed (the sample dataset does this when most of the US has the same
growing seasons for a food, then exceptions are listed). The data
accompanying each geo key is a 2-element list with the first and last
month(s) when this foodstuff is grown (integers in the range 1-12, where 1
is January, 2 is February and so forth). It's normal sometimes that the
numeric value of the first month may be larger than the last, as happens for
winter produce that might begin late in the year and end early the next year,
the period "wraps around." Occasionally there will be 4 values, if there's
two disjoint seasons for a foodstuff (though this might just be gaps in the
source dataset).

In the future, for each foodstuff, special keys (maybe beginning with an
understore to distinguish from geo keys) might be used to attach metadata
to each -- popular dishes or cuisines for it, URLs or filenames for images
and so forth. Not currently implemented, but that's the thought.
"""
