API_VERSION = '1.0'

from pyutil.assertutil import precondition

import urllib

from simplegeo.shared import APIError, Feature, SIMPLEGEOHANDLE_RSTR, is_simplegeohandle, json_decode, is_valid_lat, is_valid_lon, is_numeric
from simplegeo.shared import Client as SGClient

endpoints = {
    'create': 'places',
    'search': 'places/%(lat)s,%(lon)s.json%(quargs)s',
    }

class Client(SGClient):
    def __init__(self, key, secret, api_version=API_VERSION, host="api.simplegeo.com", port=80):
        SGClient.__init__(self, key, secret, api_version=api_version, host=host, port=port)
        self.endpoints.update(endpoints)

    def add_feature(self, feature):
        """Create a new feature, returns the simplegeohandle. """
        endpoint = self._endpoint('create')
        if feature.id:
            # only simplegeohandles or None should be stored in self.id
            assert is_simplegeohandle(feature.id)
            raise ValueError('A feature cannot be added to the Places database when it already has a simplegeohandle: %s' % (feature.id,))
        jsonrec = feature.to_json()
        resp, content = self._request(endpoint, "POST", jsonrec)
        if resp['status'] != "202":
            raise APIError(int(resp['status']), content, resp)
        contentobj = json_decode(content)
        if not contentobj.has_key('id'):
            raise APIError(int(resp['status']), content, resp)
        handle = contentobj['id']
        assert is_simplegeohandle(handle)
        return handle

    def update_feature(self, feature):
        """Update a Places feature."""
        endpoint = self._endpoint('feature', simplegeohandle=feature.id)
        return self._request(endpoint, 'POST', feature.to_json())[1]

    def delete_feature(self, simplegeohandle):
        """Delete a Places feature."""
        precondition(is_simplegeohandle(simplegeohandle), "simplegeohandle is required to match the regex %s" % SIMPLEGEOHANDLE_RSTR, simplegeohandle=simplegeohandle)
        endpoint = self._endpoint('feature', simplegeohandle=simplegeohandle)
        return self._request(endpoint, 'DELETE')[1]

    def search(self, lat, lon, radius=None, query=None, category=None):
        """Search for places near a lat/lon."""
        precondition(is_valid_lat(lat), lat)
        precondition(is_valid_lon(lon), lon)
        precondition(radius is None or is_numeric(radius), radius)
        precondition(query is None or isinstance(query, basestring), query)
        precondition(category is None or isinstance(category, basestring), category)

        kwargs = { }
        if radius:
            kwargs['radius'] = radius
        if query:
            kwargs['q'] = query
        if category:
            kwargs['category'] = category
        quargs = urllib.urlencode(kwargs)
        if quargs:
            quargs = '?'+quargs
        endpoint = self._endpoint('search', lat=lat, lon=lon, quargs=quargs)

        result = self._request(endpoint, 'GET')[1]

        fc = json_decode(result)
        return [Feature.from_dict(f) for f in fc['features']]
