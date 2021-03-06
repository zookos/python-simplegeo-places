import unittest
from pyutil import jsonutil as json
from simplegeo.places import Client, Feature, APIError
from simplegeo.shared import DecodeError

from decimal import Decimal as D

import mock

MY_OAUTH_KEY = 'MY_OAUTH_KEY'
MY_OAUTH_SECRET = 'MY_SECRET_KEY'
TESTING_LAYER = 'TESTING_LAYER'

API_VERSION = '1.0'
API_HOST = 'api.simplegeo.com'
API_PORT = 80

ENDPOINT_DESCR=json.dumps({
        "GET /1.0/features/<handle:[a-zA-Z0-9\\.,_-]+>.json": "Return a feature for a place.",
        "POST /1.0/features/<handle:.*>.json": "Update a feature.",
        "GET /1.0/places/<lat:-?[0-9\\.]+>,<lon:-?[0-9\\.]+>.json": "Search for places near a lat/lon. Query string includes ?q=term and ?q=term&category=cat",
        "POST /1.0/places": "Create a new record, returns the handle",
        "GET /1.0/debug/<number:\\d+>": "Undocumented.",
        "DELETE /1.0/features/<handle:.*>.json": "Delete a feature."})



class ClientTest(unittest.TestCase):
    def setUp(self):
        self.client = Client(MY_OAUTH_KEY, MY_OAUTH_SECRET, API_VERSION, API_HOST, API_PORT)

    def test_wrong_endpoint(self):
        self.assertRaises(Exception, self.client._endpoint, 'featuret')

    def test_missing_argument(self):
        self.assertRaises(Exception, self.client._endpoint, 'features')


    def test_add_feature_norecord_id(self):
        mockhttp = mock.Mock()
        handle = 'SG_abcdefghijklmnopqrstuv'
        newloc = 'http://api.simplegeo.com:80/%s/places/%s.json' % (API_VERSION, handle)
        resultfeature = Feature((D('11.03'), D('10.03')), simplegeohandle=handle)
        methods_called = []
        def mockrequest2(*args, **kwargs):
            methods_called.append(('request', args, kwargs))
            return ({'status': '200', 'content-type': 'application/json', }, resultfeature.to_json())

        def mockrequest(*args, **kwargs):
            self.assertEqual(args[0], 'http://api.simplegeo.com:80/%s/places' % (API_VERSION,))
            self.assertEqual(args[1], 'POST')

            bodyobj = json.loads(kwargs['body'])
            self.failUnlessEqual(bodyobj['id'], None)
            methods_called.append(('request', args, kwargs))
            mockhttp.request = mockrequest2
            return ({'status': '202', 'content-type': 'application/json', 'location': newloc}, json.dumps({'id': handle}))

        mockhttp.request = mockrequest
        self.client.http = mockhttp

        feature = Feature(
            coordinates=(D('37.8016'), D('-122.4783'))
        )

        res = self.client.add_feature(feature)
        self.failUnlessEqual(res, handle)

    def test_add_feature_simplegeohandle(self):
        handle = 'SG_abcdefghijklmnopqrstuv'
        feature = Feature(
            simplegeohandle=handle,
            coordinates=(D('37.8016'), D('-122.4783'))
        )

        # You can't add-feature on a feature that already has a simplegeo handle. Don't do that.
        self.failUnlessRaises(ValueError, self.client.add_feature, feature)

    def test_add_feature_simplegeohandle_and_record_id(self):
        handle = 'SG_abcdefghijklmnopqrstuv'
        record_id = 'this is my record #1. my first record. and it is mine'
        feature = Feature(
            simplegeohandle=handle,
            properties={'record_id': record_id},
            coordinates = (D('37.8016'), D('-122.4783'))
        )

        # You can't add-feature on a feature that already has a simplegeo handle. Don't do that.
        self.failUnlessRaises(ValueError, self.client.add_feature, feature)

    def test_add_feature_record_id(self):
        mockhttp = mock.Mock()
        handle = 'SG_abcdefghijklmnopqrstuv'
        record_id = 'this is my record #1. my first record. and it is mine'
        newloc = 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle)
        resultfeature = Feature((D('11.03'), D('10.03')), simplegeohandle=handle)
        methods_called = []
        def mockrequest2(*args, **kwargs):
            methods_called.append(('request', args, kwargs))
            return ({'status': '200', 'content-type': 'application/json', }, resultfeature.to_json())

        def mockrequest(*args, **kwargs):
            self.failUnlessEqual(args[0], 'http://api.simplegeo.com:80/%s/places' % (API_VERSION,))
            self.failUnlessEqual(args[1], 'POST')
            bodyobj = json.loads(kwargs['body'])
            self.failUnlessEqual(bodyobj['properties'].get('record_id'), record_id)
            methods_called.append(('request', args, kwargs))
            mockhttp.request = mockrequest2
            return ({'status': '202', 'content-type': 'application/json', 'location': newloc}, json.dumps({'id': handle}))

        mockhttp.request = mockrequest
        self.client.http = mockhttp

        feature = Feature(
            properties={'record_id': record_id},
            coordinates = (D('37.8016'), D('-122.4783'))
        )

        res = self.client.add_feature(feature)
        self.failUnlessEqual(res, handle)

    def test_get_feature(self):
        handle = 'SG_abcdefghijklmnopqrstuv'
        resultfeature = Feature((D('11.03'), D('10.03')), simplegeohandle=handle)

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, resultfeature.to_json())
        self.client.http = mockhttp

        res = self.client.get_feature(handle)
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')
        self.failUnless(isinstance(res, Feature), res)
        self.assertEqual(res.to_json(), resultfeature.to_json())

    def test_type_check_request(self):
        self.failUnlessRaises(TypeError, self.client._request, 'whatever', 'POST', {'bogus': "non string"})

    def test_empty_body(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, None)
        self.client.http = mockhttp

        self.client._request("http://anyrandomendpoint", 'POST')

        self.failUnless(mockhttp.method_calls[0][2]['body'] is None, (repr(mockhttp.method_calls[0][2]['body']), type(mockhttp.method_calls[0][2]['body'])))

    def test_dont_json_decode_results(self):
        """ _request() is required to return the exact string that the HTTP
        server sent to it -- no transforming it, such as by json-decoding. """

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, '{ "Hello": "I am a string. \xe2\x9d\xa4" }'.decode('utf-8'))
        self.client.http = mockhttp
        res = self.client._request("http://thing", 'POST')[1]
        self.failUnlessEqual(res, '{ "Hello": "I am a string. \xe2\x9d\xa4" }'.decode('utf-8'))

    def test_dont_Featureify_results(self):
        """ _request() is required to return the exact string that the HTTP
        server sent to it -- no transforming it, such as by json-decoding and
        then constructing a Feature. """

        EXAMPLE_RECORD_JSONSTR=json.dumps({ 'geometry' : { 'type' : 'Point', 'coordinates' : [D('10.0'), D('11.0')] }, 'id' : 'my_id', 'type' : 'Feature', 'properties' : { 'key' : 'value'  , 'type' : 'object' } })

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_RECORD_JSONSTR)
        self.client.http = mockhttp
        res = self.client._request("http://thing", 'POST')[1]
        self.failUnlessEqual(res, EXAMPLE_RECORD_JSONSTR)

    def test_update_feature(self):
        handle = 'SG_abcdefghijklmnopqrstuv'
        rec = Feature((D('11.03'), D('10.04')), simplegeohandle=handle)

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, {'token': "this is your polling token"})
        self.client.http = mockhttp

        res = self.client.update_feature(rec)
        self.failUnless(isinstance(res, dict), res)
        self.failUnless(res.has_key('token'), res)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'POST')
        bodyjson = mockhttp.method_calls[0][2]['body']
        self.failUnless(isinstance(bodyjson, basestring), (repr(bodyjson), type(bodyjson)))
        # If it decoded as valid json then check for some expected fields
        bodyobj = json.loads(bodyjson)
        self.failUnless(bodyobj.get('geometry').has_key('coordinates'), bodyobj)
        self.failUnless(bodyobj.get('geometry').has_key('type'), bodyobj)
        self.failUnlessEqual(bodyobj.get('geometry')['type'], 'Point')

    def test_delete_feature(self):
        handle = 'SG_abcdefghijklmnopqrstuv'

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, "whatever the response body is")
        self.client.http = mockhttp

        res = self.client.delete_feature(handle)
        self.failUnlessEqual(res, "whatever the response body is")

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'DELETE')

    def test_search(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.http = mockhttp

        self.failUnlessRaises(AssertionError, self.client.search, -91, 100)
        self.failUnlessRaises(AssertionError, self.client.search, -81, 181)

        lat = D('11.03')
        lon = D('10.04')
        res = self.client.search(lat, lon, query='monkeys', category='animal')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/%s,%s.json?q=monkeys&category=animal' % (API_VERSION, lat, lon))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_radius_search(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': []}))
        self.client.http = mockhttp

        lat = D('11.03')
        lon = D('10.04')
        radius = D('0.01')
        res = self.client.search(lat, lon, radius=radius)
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 0)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/%s,%s.json?radius=%s' % (API_VERSION, lat, lon, radius))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_lat_lon_search(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.http = mockhttp

        lat = D('11.03')
        lon = D('10.04')
        res = self.client.search(lat, lon)
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/%s,%s.json' % (API_VERSION, lat, lon))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_get_feature_bad_json(self):
        handle = 'SG_abcdefghijklmnopqrstuv'

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, 'some crap')
        self.client.http = mockhttp

        try:
            self.client.get_feature(handle)
        except DecodeError, e:
            self.failUnlessEqual(e.code,None,repr(e.code))
            self.failUnless("Could not decode JSON" in e.msg, repr(e.msg))
            repr(e)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')


    def test_APIError(self):
        e = APIError(500, 'whee', {'status': "500"})
        self.failUnlessEqual(e.code, 500)
        self.failUnlessEqual(e.msg, 'whee')
        repr(e)
        str(e)

    def test_get_places_error(self):
        handle = 'SG_abcdefghijklmnopqrstuv'

        mockhttp = mock.Mock()
        # mockhttp.request.return_value = ({'status': '500', 'content-type': 'application/json', }, None)
        mockhttp.request.return_value = ({'status': '500', 'content-type': 'application/json', }, '{"message": "help my web server is confuzzled"}')
        self.client.http = mockhttp

        try:
            self.client.get_feature(handle)
        except APIError, e:
            self.failUnlessEqual(e.code, 500, repr(e.code))
            self.failUnlessEqual(e.msg, '{"message": "help my web server is confuzzled"}', (type(e.msg), repr(e.msg)))

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')
