from unittest import TestCase, mock
from unittest.mock import Mock

from kg_obo.obolibrary_utils import base_url_if_exists


class TestOboLibraryUtils(TestCase):

    def setUp(self) -> None:
        pass

    def test_reality(self):
        self.assertEqual(1, 1)

    @mock.patch('requests.head')
    @mock.patch('urllib.request.urlopen')
    def test_base_url_if_exists(self, mock_urlopen, mock_head):
        mock_head.return_value = Mock(status_code=200)
        base_url_if_exists("test")
        self.assertTrue(mock_head.called)
        self.assertTrue(mock_urlopen.called)
