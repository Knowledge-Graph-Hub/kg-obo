from unittest import TestCase, mock
from unittest.mock import Mock

from kg_obo.obolibrary_utils import get_url, base_url_exists


class TestOboLibraryUtils(TestCase):

    def setUp(self) -> None:
        self.url_values = "1\n2\n3\n"
        pass

    @mock.patch('requests.head')
    @mock.patch('urllib.request.urlopen')
    def test_get_url(self, mock_urlopen, mock_head):
        for status in 200, 404:
            mock_head.return_value = Mock(status_code=status)
            mock_urlopen.return_value = self.url_values
            ret_url = get_url("test")
            self.assertTrue(mock_head.called)
            self.assertTrue(mock_urlopen.called)
            if status == 200:
                self.assertEqual(ret_url, "http://purl.obolibrary.org/obo/test/test.owl")
            else:
                self.assertEqual(ret_url, "http://purl.obolibrary.org/obo/test.owl")
            

    @mock.patch('requests.head')
    @mock.patch('urllib.request.urlopen')
    def test_base_url_exists(self, mock_urlopen, mock_head):
        for status in 200, 404:
            mock_head.return_value = Mock(status_code=status)
            mock_urlopen.return_value = self.url_values
            base_exists = base_url_exists("test")
            self.assertTrue(mock_head.called)
            self.assertTrue(mock_urlopen.called)
            if status == 200:
                self.assertTrue(base_exists)
            else:
                self.assertFalse(base_exists)

