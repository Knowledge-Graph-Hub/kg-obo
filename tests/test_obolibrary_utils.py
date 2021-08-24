from unittest import TestCase, mock
from unittest.mock import Mock

from kg_obo.obolibrary_utils import base_url_if_exists


class TestOboLibraryUtils(TestCase):

    def setUp(self) -> None:
        pass

    @mock.patch('requests.head')
    @mock.patch('urllib.request.urlopen')
    def test_base_url_if_exists(self, mock_urlopen, mock_head):
        for status in 200, 404:
            mock_head.return_value = Mock(status_code=status)
            mock_urlopen.return_value = [1, 2, 3]
            ret_url = base_url_if_exists("test")
            self.assertTrue(mock_head.called)
            self.assertTrue(mock_urlopen.called)
            self.assertEqual(ret_url, "http://purl.obolibrary.org/obo/test.owl")

