# -*- coding: utf-8 -*-
import json
import unittest
from unittest.mock import patch

from stix_shifter.stix_transmission.stix_transmission import StixTransmission

from stix_shifter_modules.infoblox.entry_point import EntryPoint
from stix_shifter_modules.infoblox.stix_transmission.api_client import APIClient
from tests.utils.async_utils import get_mock_response, RequestMockResponse

CONNECTION = {"host": "mock-host.test","port": 443,"options": {"timeout": 60, "result_limit": 1000}}
CONFIG = {"auth": {"token": "token"}}
MODULE = "infoblox"

class MockResponse:
    def __init__(self, response_code, obj):
        self.code = response_code
        self.object = obj

    def read(self):
        return bytearray(self.object, 'utf-8')

class TestTransmission(unittest.TestCase):
    def test_is_async(self):
        entry_point = EntryPoint(CONNECTION, CONFIG)
        check_async = entry_point.is_async()
        self.assertFalse(check_async)

    def test_result_limit_too_large(self):
        connection = {"host": "mock-host.test","port": 443,"options": {"timeout": 60, "result_limit": 5000000}}

        api_client = APIClient(connection, CONFIG)
        self.assertEqual(api_client.result_limit, 10000)

    ###############################
    ## PING
    ###############################
    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_ping(self, mock_ping):
        response = {"threat": [{"id": "3a7c0318-e985-11eb-93d6-438342be5508","type": "HOST","host": "xbug.uk.to"}],"record_count": 1}
        mock_ping.side_effect = [get_mock_response(200, json.dumps(response), 'byte')]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        ping_response = transmission.ping()
        self.assertEqual(ping_response, {'success': True})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_ping_failure(self, mock_ping):
        response = {"error": [{"message": "Invalid type hst --- type must be one of (host, ip, url, email, hash)"}]}
        mock_ping.side_effect = [get_mock_response(400, json.dumps(response), 'byte')]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        ping_response = transmission.ping()
        self.assertEqual(ping_response, {'code': 'invalid_parameter','connector': 'infoblox','error': 'infoblox connector error => {"error": [{"message": "Invalid type hst --- type must be one of (host, ip, url, email, hash)"}]}','success': False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_ping_auth_failure(self, mock_ping):
        response = '<html><head><title>401 Authorization Required</title></head><body><center><h1>401 Authorization Required</h1></center><hr><center>nginx</center></body></html>'
        mock_ping.side_effect = [get_mock_response(401, response, 'byte')]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        ping_response = transmission.ping()
        self.assertEqual(ping_response, {'code': 'authentication_fail',
            'connector': 'infoblox',
            'error': 'infoblox connector error => <html><head><title>401 Authorization Required</title></head><body><center><h1>401 Authorization Required</h1></center><hr><center>nginx</center></body></html>',
            'success': False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_ping_unknown_failure(self, mock_ping):
        response = {"error": {"code": "InternalError",}}
        mock_ping.side_effect = [get_mock_response(503, json.dumps(response), 'byte')]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        ping_response = transmission.ping()
        self.assertEqual(ping_response, {'code': 'unknown','connector': 'infoblox','error': 'infoblox connector error => {"error": {"code": "InternalError"}}','success': False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_ping_unknown_code(self, mock_ping):
        response = {"error": {"code": "InternalError",}}
        mock_ping.side_effect = [get_mock_response(None, json.dumps(response), 'byte')]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        ping_response = transmission.ping()
        self.assertEqual(ping_response, {'code': 'unknown','connector': 'infoblox','error': 'infoblox connector error => {"error": {"code": "InternalError"}}','success': False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_ping_exception(self, mock_ping):
        mock_ping.side_effect = ConnectionError("Failed to establish a new connection")
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        ping_response = transmission.ping()
        self.assertEqual(ping_response, {'code': 'service_unavailable', 'connector': 'infoblox', 'error': "infoblox connector error => Failed to establish a new connection", 'success': False})

    ###############################
    ## QUERY
    ###############################
    def test_query(self):
        # tests QueryConnector.create_query_connection
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        query_response = transmission.query(self._get_query())
        self.assertEqual(query_response, {"success": True,"search_id": self._get_query()})

    ###############################
    ## RESULTS
    ###############################
    @staticmethod
    def _get_query(source="unknown_source"):
        query = {"offset": 0,"fields": [],"from": 1587892612,"to": 1592382065,"source": source,"query": "hostName:*"}

        return json.dumps(query)

    def test_results_missing_source(self):
        # tests ResultsConnector.create_results_connection
        query = json.dumps({"offset": 0,"fields": [],"from": 1587892612,"to": 1592382065,"query": "hostName:*"})
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(query, 0, 10)
        self.assertEqual(results_response, {'code': 'unknown', 'connector': 'infoblox', 'error': "infoblox connector error => 'source'", 'success': False})

    def test_results_unknown_source(self):
        # tests ResultsConnector.create_results_connection
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(), 0, 10)
        self.assertEqual(results_response, {'code': 'unknown', 'connector': 'infoblox', 'error': "infoblox connector error => Unknown source provided source=unknown_source", 'success': False})

    ###############################
    ## STATUS
    ###############################
    def test_status(self):
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        status_response = transmission.status("search_id")
        self.assertEqual(status_response, {'progress': 100, 'status': 'COMPLETED', 'success': True})

    ###############################
    ## DELETE
    ###############################
    def test_delete(self):
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        status_response = transmission.delete("search_id")
        self.assertEqual(status_response, {'success': True})

class TestDnsEventTransmission(unittest.TestCase):
    def get_dialect(self):
        return "dnsEventData"

    ###############################
    ## RESULTS - dnsEventData
    ###############################
    def _get_query(self):
        query = {"offset": 0, "fields": [], "from": 1587892612, "to": 1592382065, "source": self.get_dialect(), "query": "hostName:*"}

        return json.dumps(query)

    @staticmethod
    def _get_response(count=1):
        response = {"result": []}
        for i in range(0, count):
            response["result"].append({"qip": "1.1.1.1"})

        return json.dumps(response)

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_invalid_param(self, mock_query):
        payload = {"error": [{"message": "Invalid arguments, t0/t1 are required parameters"}]}
        mock_query.side_effect = [get_mock_response(400, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(), 0, 10)
        self.assertEqual(results_response, {"code": "invalid_parameter", 'connector': 'infoblox', "error": 'infoblox connector error => '+ payload["error"][0]["message"],"success": False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_auth_failure(self, mock_query):
        payload = '<html><head><title>401 Authorization Required</title></head><body><center><h1>401 Authorization Required</h1></center><hr><center>nginx</center></body></html>'
        mock_query.side_effect = [get_mock_response(401, payload, 'byte')]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(), 0, 10)
        self.assertEqual(results_response, {"code": "authentication_fail", 'connector': 'infoblox', "error": 'infoblox connector error => '+payload,"success": False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_no_results(self, mock_query):
        payload = {"result": [],"status_code": "200"}
        mock_query.side_effect = [get_mock_response(200, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(), 0, 10)
        self.assertEqual(results_response, {'data': [], 'success': True})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_all_results(self, mock_query):
        payload = {"result": [{"qip": "1.1.1.1"},{"qip": "1.1.1.2"}],"status_code": "200"}
        mock_query.side_effect = [get_mock_response(200, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(), 0, 1)
        self.assertEqual(results_response, {"success": True,"data": [{"dnsEventData": {"qip": "1.1.1.1"}}]})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_max_fetch(self, mock_query):
        mock_query.side_effect = [get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.1"}]})),get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.2"}]})),
                get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.3"}]})),get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.4"}]})),
                get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.5"}]})),get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.6"}]})),
                get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.7"}]})),get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.8"}]})),
                get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.9"}]})),get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.10"}]})),
                RequestMockResponse(200, json.dumps({"result": [{"qip": "1.1.1.11"}]}))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(), 0, 20)
        self.assertEqual(results_response, {"success": True,"data": [
                {"dnsEventData": {"qip": "1.1.1.1"}},{"dnsEventData": {"qip": "1.1.1.2"}},{"dnsEventData": {"qip": "1.1.1.3"}},{"dnsEventData": {"qip": "1.1.1.4"}},
                {"dnsEventData": {"qip": "1.1.1.5"}},{"dnsEventData": {"qip": "1.1.1.6"}},{"dnsEventData": {"qip": "1.1.1.7"}},{"dnsEventData": {"qip": "1.1.1.8"}},
                {"dnsEventData": {"qip": "1.1.1.9"}},{"dnsEventData": {"qip": "1.1.1.10"}}]})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_too_many_results(self, mock_query):
        mock_query.side_effect = [
                get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.1"}, {"qip": "1.1.1.2"}]})),get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.3"}, {"qip": "1.1.1.4"}]})),
                get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.5"}, {"qip": "1.1.1.6"}]})),RequestMockResponse(200, json.dumps({"result": [{"qip": "1.1.1.7"}, {"qip": "1.1.1.8"}]})),
                RequestMockResponse(200, json.dumps({"result": [{"qip": "1.1.1.9"}, {"qip": "1.1.1.10"}]}))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(), 0, 4)
        self.assertEqual(results_response, {"success": True,"data": [
                {"dnsEventData": {"qip": "1.1.1.1"}},{"dnsEventData": {"qip": "1.1.1.2"}},{"dnsEventData": {"qip": "1.1.1.3"}},{"dnsEventData": {"qip": "1.1.1.4"}}]})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_min_range(self, mock_query):
        mock_query.side_effect = [
                get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.5"}, {"qip": "1.1.1.6"}]})),
                get_mock_response(200, json.dumps({"result": [{"qip": "1.1.1.7"}, {"qip": "1.1.1.8"}]})),
                RequestMockResponse(200, json.dumps({"result": [{"qip": "1.1.1.9"}, {"qip": "1.1.1.10"}]}))
            ]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(), 4, 3)
        self.assertEqual(results_response, {"success": True,"data": [{"dnsEventData": {"qip": "1.1.1.5"}},{"dnsEventData": {"qip": "1.1.1.6"}},{"dnsEventData": {"qip": "1.1.1.7"}}]})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_different_offsets(self, mock_results):
        mocks = [(get_mock_response(200, self._get_response(500)))]

        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(), 0, 200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 200)

        mocks = [(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500)))]

        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(), 0, 500)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 500)

        mocks = [(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500)))]

        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(), 0, 1200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 1200)

        mocks = [(get_mock_response(200, self._get_response(500)))]

        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(), 99, 200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 200)

        mocks = [(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500)))]

        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(), 99, 500)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 500)

        mocks = [(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500)))]

        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(), 99, 1200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 1200)

        mocks = [(get_mock_response(200, self._get_response(500)))]

        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(), 600, 100)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 100)

        mocks = [(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),
                (get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),
                (get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),
                (get_mock_response(200, self._get_response(500)))]

        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(), 0, 5000)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 5000)

        mocks = [(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),
                (get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),
                (get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),
                (get_mock_response(200, self._get_response(500)))]

        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(), 0, 10000)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 5000)

        mocks = [(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),
                (get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),
                (get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),(get_mock_response(200, self._get_response(500))),
                (get_mock_response(200, self._get_response(500)))]

        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(), 5000, 10000)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 5000)

        mocks = [(get_mock_response(200, self._get_response(500)))]

        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(), 4999, 1)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 1)

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_exception(self, mock_ping):
        mock_ping.side_effect = ConnectionError("Failed to establish a new connection")
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(), 4, 3)
        self.assertEqual(results_response, {"success": False,'connector': 'infoblox',"error": "infoblox connector error => Failed to establish a new connection","code": "service_unavailable"})

class TestDossierTransmission(unittest.TestCase):
    def get_dialect(self):
        return "dossierData"

    ###############################
    ## RESULTS - dossierData
    ###############################
    def _get_query(self, threat_type=None):
        query = {"offset": 0,"fields": [],"from": 1587892612,"to": 1592382065,"source": self.get_dialect(),"query": "hostName:*"}

        if threat_type:
            query["threat_type"] = threat_type

        return json.dumps(query)

    @staticmethod
    def _get_response(count=1):
        response = {"status": "success","job": {"create_time": "2021-08-01T20:55:48.542Z"},"results": [{"status": "success","data": {"duration": 243602755,"threat": []}}]}

        for i in range(0, count):
            response["results"][0]["data"]["threat"].append({"batch_id": i+1,"class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"})

        return json.dumps(response)

    def test_results_missing_threat_type(self):
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(), 0, 10)
        self.assertEqual(results_response, {'code': 'unknown', 'connector': 'infoblox', 'error': "infoblox connector error => 'threat_type'", 'success': False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_invalid_param(self, mock_query):
        payload = {"status": "error","error": "unknown target type"}
        mock_query.side_effect = [get_mock_response(400, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="unknown_type"), 0, 10)
        self.assertEqual(results_response, {'code': 'invalid_parameter', 'connector': 'infoblox', 'error': 'infoblox connector error => unknown target type','success': False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_auth_failure(self, mock_query):
        payload = '<html><head><title>401 Authorization Required</title></head><body><center><h1>401 Authorization Required</h1></center><hr><center>nginx</center></body></html>'
        mock_query.side_effect = [get_mock_response(401, payload, 'byte')]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="unknown_type"), 0, 10)
        self.assertEqual(results_response, {'code': 'authentication_fail', 'connector': 'infoblox', 'error': 'infoblox connector error => '+payload,'success': False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_no_results_1(self, mock_query):
        payload = {"status": "success","job": {"create_time": "2021-08-01T20:55:48.542Z"},"results": []}
        mock_query.side_effect = [get_mock_response(200, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="host"), 0, 10)
        self.assertEqual(results_response, {'data': [], 'success': True})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_no_results_2(self, mock_query):
        payload = {"status": "success","job": {"create_time": "2021-08-01T20:55:48.542Z"},"results": [{"status": "success","data": {"duration": 243602755,"threat": []}}]}
        mock_query.side_effect = [get_mock_response(200, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="host"), 0, 10)
        self.assertEqual(results_response, {'data': [], 'success': True})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_all_results(self, mock_query):
        payload = {"status": "success","job": {"create_time": "2021-08-01T20:55:48.542Z"},"results": [
            {"status": "success","data": {"duration": 243602755,"threat": [{"batch_id": "1","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"}]}}]}
        mock_query.side_effect = [get_mock_response(200, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="host"), 0, 10)
        self.assertEqual(results_response, {"success": True,"data": [{"dossierData": {"job": {"create_time": "2021-08-01T20:55:48.542Z"},
                "results": [{"data": {"threat": [{"batch_id": "1","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"}]}}]}}]})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_too_many_results(self, mock_query):
        payload = {"status": "success","job": {"create_time": "2021-08-01T20:55:48.542Z"},"results": [{"status": "success","data": {"duration": 243602755,"threat": [
            {"batch_id": "1","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"},
            {"batch_id": "2","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"},
            {"batch_id": "3","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"},
            {"batch_id": "4","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"},
            {"batch_id": "5","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"}]}}]}
        mock_query.side_effect = [get_mock_response(200, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="host"), 0, 2)
        self.assertEqual(results_response, {"success": True,"data": [{"dossierData": {"job": {"create_time": "2021-08-01T20:55:48.542Z"},
            "results": [{"data": {"threat": [{"batch_id": "1","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"}]}}]}},{
            "dossierData": {"job": {"create_time": "2021-08-01T20:55:48.542Z"},"results": [{"data": {"threat": [{"batch_id": "2","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"}]}}]}}]})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_min_range(self, mock_query):
        payload = {"status": "success","job": {"create_time": "2021-08-01T20:55:48.542Z"},"results": [{"status": "success","data": {"duration": 243602755,
            "threat": [{"batch_id": "1","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"},
            {"batch_id": "2","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"},
            {"batch_id": "3","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"},
            {"batch_id": "4","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"},
            {"batch_id": "5","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"}]}}]}
        mock_query.side_effect = [get_mock_response(200, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="host"), 4, 10)
        self.assertEqual(results_response, {"success": True,"data": [
                {"dossierData": {"job": {"create_time": "2021-08-01T20:55:48.542Z"},"results": [{"data": {"threat": [{"batch_id": "5","class": "Suspicious","confidence": 100,"confidence_score": 8,"confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:N/CP:F","detected": "2022-08-20T16:56:32.990Z","dga": "false","domain": "example.com","expiration": "2022-12-18T16:56:32.990Z","extended": {"cyberint_guid": "bb73a8ed37bc7081b494e73b149d54fe","no_whitelist": "false","notes": "Name server domains associated with high risk domains."},"full_profile": "IID:ANALYST","host": "example.com","id": "cfdde1d9-20a9-11ed-82da-e59311f5c6a9","imported": "2022-08-20T17:02:02.608Z","profile": "IID","property": "Suspicious_Nameserver","received": "2022-08-20T17:02:02.608Z","risk_score": 5,"risk_score_rating": "Medium","risk_score_vector": "RSIS:1.0/TSS:M/TLD:N/CVSS:L/EX:N/MOD:L/AVL:L/T:M/DT:L","threat_level": 60,"threat_score": 3.6,"threat_score_rating": "Medium","threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:N/MOD:L/AVL:L/CI:N/ASN:N/TLD:N/DOP:N/P:F","tld": "com","type": "HOST","up": "true"}]}}]}}]})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_different_offsets(self, mock_results):
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 0, 200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 200)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 0, 500)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 500)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 0, 1200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 1000)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 99, 200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 200)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 99, 500)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 500)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 99, 1200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 901)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 600, 100)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 100)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 0, 5000)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 1000)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 0, 10000)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 1000)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 5000, 10000)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 0)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 999, 1)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 1)

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_exception(self, mock_ping):
        mock_ping.side_effect = ConnectionError("Failed to establish a new connection")
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="host"), 4, 3)
        self.assertEqual(results_response, {"success": False,'connector': 'infoblox',"error": "infoblox connector error => Failed to establish a new connection","code": "service_unavailable"})

class TestTideDbTransmission(unittest.TestCase):
    def get_dialect(self):
        return "tideDbData"

    ###############################
    ## RESULTS - tideDbData
    ###############################
    def _get_query(self, threat_type=None):
        query = {"offset": 0,"fields": [],"from": 1587892612,"to": 1592382065,"source": self.get_dialect(),"query": "hostName:*"}

        if threat_type:
            query["threat_type"] = threat_type

        return json.dumps(query)

    @staticmethod
    def _get_response(count=1):
        response = {"threat": []}
        for i in range(0, count):
            response["threat"].append({"ip": "1.1.1.1"})

        return json.dumps(response)

    def test_results_missing_threat_type(self):
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(), 0, 10)
        self.assertEqual(results_response, {'code': 'unknown', 'connector': 'infoblox', 'error': "infoblox connector error => 'threat_type'", 'success': False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_invalid_param(self, mock_query):
        payload = {"status": "error","error": "unknown target type"}
        mock_query.side_effect = [get_mock_response(400, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="unknown_type"), 0, 10)
        self.assertEqual(results_response, {'code': 'invalid_parameter', 'connector': 'infoblox', 'error': 'infoblox connector error => unknown target type','success': False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_auth_failure(self, mock_query):
        payload = '<html><head><title>401 Authorization Required</title></head><body><center><h1>401 Authorization Required</h1></center><hr><center>nginx</center></body></html>'
        mock_query.side_effect = [get_mock_response(401, payload, 'byte')]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="unknown_type"), 0, 10)
        self.assertEqual(results_response, {'code': 'authentication_fail', 'connector': 'infoblox', 'error': 'infoblox connector error => ' + payload,'success': False})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_no_results(self, mock_query):
        payload = {"threat": []}
        mock_query.side_effect = [get_mock_response(200, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="host"), 0, 10)
        self.assertEqual(results_response, {'data': [], 'success': True})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_all_results(self, mock_query):
        payload = {"threat": [{"id": "1af2936f-9d33-11eb-8943-6962d4bdf9de","type": "HOST","host": "1-lntesasanpaolo-portaleweb.xyz","domain": "1-lntesasanpaolo-portaleweb.xyz",
                "tld": "xyz","profile": "IID","property": "Phishing_Generic","class": "Phishing","threat_level": 100,"confidence": 100,"detected": "2021-04-14T15:04:26.116Z",
                "received": "2021-04-14T15:07:18.592Z","imported": "2021-04-14T15:07:18.592Z","expiration": "2022-04-14T15:04:26.116Z","dga": False,"up": True,
                "batch_id": "1af24549-9d33-11eb-8943-6962d4bdf9de","threat_score": 6,"threat_score_rating": "Medium",
                "threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:H/MOD:N/AVL:N/CI:N/ASN:N/TLD:H/DOP:N/P:F","confidence_score": 8.2,
                "confidence_score_rating": "High","confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:H/CP:F","risk_score": 7.9,"risk_score_rating": "High",
                "risk_score_vector": "RSIS:1.0/TSS:M/TLD:H/CVSS:L/EX:H/MOD:N/AVL:N/T:M/DT:L","extended": {"cyberint_guid": "dadbdde3eaf7fd97bae0bdec8c6ceb07"}}]
        }
        mock_query.side_effect = [get_mock_response(200, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="host"), 0, 10)
        self.assertEqual(results_response, {"success": True,"data": [{"tideDbData": {"id": "1af2936f-9d33-11eb-8943-6962d4bdf9de","type": "HOST","host": "1-lntesasanpaolo-portaleweb.xyz",
                "domain": "1-lntesasanpaolo-portaleweb.xyz","tld": "xyz","profile": "IID","property": "Phishing_Generic","class": "Phishing","threat_level": 100,"confidence": 100,
                "detected": "2021-04-14T15:04:26.116Z","received": "2021-04-14T15:07:18.592Z","imported": "2021-04-14T15:07:18.592Z","expiration": "2022-04-14T15:04:26.116Z",
                "dga": False,"up": True,"batch_id": "1af24549-9d33-11eb-8943-6962d4bdf9de","threat_score": 6,"threat_score_rating": "Medium",
                "threat_score_vector": "TSIS:1.0/AV:N/AC:L/PR:L/UI:R/EX:H/MOD:N/AVL:N/CI:N/ASN:N/TLD:H/DOP:N/P:F","confidence_score": 8.2,"confidence_score_rating": "High",
                "confidence_score_vector": "COSIS:1.0/SR:H/POP:N/TLD:H/CP:F","risk_score": 7.9,"risk_score_rating": "High","risk_score_vector": "RSIS:1.0/TSS:M/TLD:H/CVSS:L/EX:H/MOD:N/AVL:N/T:M/DT:L",
                "extended": {"cyberint_guid": "dadbdde3eaf7fd97bae0bdec8c6ceb07"}}}]
        })


    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_too_many_results(self, mock_query):
        payload = {
            "threat": [
                {"ip": "1.1.1.1"},
                {"ip": "1.1.1.2"},
                {"ip": "1.1.1.3"},
                {"ip": "1.1.1.4"},
                {"ip": "1.1.1.5"}
            ]
        }
        mock_query.side_effect = [get_mock_response(200, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="host"), 0, 2)

        # print("\n\n\n\nresult")
        # print(results_response)
        self.assertEqual(results_response, {
            "success": True,
            "data": [
                {"tideDbData": {"ip": "1.1.1.1"}},
                {"tideDbData": {"ip": "1.1.1.2"}}
            ]
        })

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_min_range(self, mock_query):
        payload = {"threat": [{"ip": "1.1.1.1"},{"ip": "1.1.1.2"},{"ip": "1.1.1.3"},{"ip": "1.1.1.4"},{"ip": "1.1.1.5"}]}
        mock_query.side_effect = [get_mock_response(200, json.dumps(payload))]
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="host"), 4, 10)
        self.assertEqual(results_response, {"success": True,"data": [{"tideDbData": {"ip": "1.1.1.5"}}]})

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_different_offsets(self, mock_results):
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 0, 200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 200)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 0, 500)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 500)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 0, 1200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 1000)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 99, 200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 200)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 99, 500)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 500)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 99, 1200)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 901)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 600, 100)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 100)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 0, 5000)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 1000)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 0, 10000)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 1000)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 5000, 10000)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 0)

        mocks = [(get_mock_response(200, self._get_response(1000))),]
        mock_results.side_effect = mocks
        result_response = transmission.results(self._get_query(threat_type="host"), 999, 1)
        self.assertTrue(result_response["success"])
        self.assertEqual(len(result_response["data"]), 1)

    @patch('stix_shifter_utils.stix_transmission.utils.RestApiClientAsync.RestApiClientAsync.call_api')
    def test_results_exception(self, mock_ping):
        mock_ping.side_effect = ConnectionError("Failed to establish a new connection")
        transmission = StixTransmission(MODULE, CONNECTION, CONFIG)
        results_response = transmission.results(self._get_query(threat_type="host"), 4, 3)
        self.assertEqual(results_response, {"success": False,'connector': 'infoblox',"error": "infoblox connector error => Failed to establish a new connection","code": "service_unavailable"})
