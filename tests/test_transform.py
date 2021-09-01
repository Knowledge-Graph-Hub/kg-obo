import logging
import tempfile
from unittest import TestCase, mock
from unittest.mock import Mock
from botocore.exceptions import ClientError

from kg_obo.transform import run_transform, kgx_transform, download_ontology, \
    get_owl_iri


class TestRunTransform(TestCase):

    def setUp(self) -> None:
        self.kgx_transform_kwargs = {'input_file': ['foo'], 'input_format': 'tsv',
                                     'output_file': 'bar', 'output_format': 'tsv',
                                     'logger': logging.Logger}

        self.download_ontology_kwargs = {'url': 'https://some/url',
                                         'file': tempfile.NamedTemporaryFile().name,
                                         'logger': logging.getLogger("fake-log")}

    @mock.patch('requests.get')
    @mock.patch('kg_obo.transform.retrieve_obofoundry_yaml')
    @mock.patch('kg_obo.obolibrary_utils.base_url_if_exists')
    @mock.patch('kg_obo.transform.get_owl_iri', return_value=('http://purl.obolibrary.org/obo/bfo/2019-08-26/bfo.owl', '2019-08-26'))
    @mock.patch('kgx.cli.transform')
    def test_run_transform(self, mock_kgx_transform, mock_get_owl_iri, mock_base_url,
                           mock_retrieve_obofoundry_yaml, mock_get):
        mock_retrieve_obofoundry_yaml.return_value = [{'id': 'bfo'}]
        with tempfile.TemporaryDirectory() as td:
            run_transform(log_dir=td)
            self.assertTrue(mock_get.called)
            self.assertTrue(mock_base_url.called)
            self.assertTrue(mock_get_owl_iri.called)
            self.assertTrue(mock_retrieve_obofoundry_yaml.called)
            self.assertTrue(mock_kgx_transform.called)

        # test that we don't run transform if download of ontology fails
        with mock.patch('kg_obo.transform.download_ontology', return_value=False),\
                tempfile.TemporaryDirectory() as td:
            mock_kgx_transform.reset_mock()
            run_transform(log_dir=td)
            self.assertFalse(mock_kgx_transform.called)

    @mock.patch('kgx.cli.transform')
    def test_kgx_transform(self, mock_kgx_transform) -> None:
        ret_val = kgx_transform(**self.kgx_transform_kwargs)
        self.assertTrue(mock_kgx_transform.called)
        self.assertTrue(ret_val[0])

    @mock.patch('kgx.cli.transform')
    def test_kgx_transform_fail(self, mock_kgx_transform) -> None:
        mock_kgx_transform.side_effect = Exception(mock.Mock())
        mock_kgx_transform.side_effect.isEnabledFor = mock.Mock()
        mock_kgx_transform.side_effect._log = mock.Mock()
        ret_val = kgx_transform(**self.kgx_transform_kwargs)
        self.assertTrue(mock_kgx_transform.called)
        self.assertFalse(ret_val[0])

    @mock.patch('requests.get')
    def test_download_ontology(self, mock_get):
        ret_val = download_ontology(**self.download_ontology_kwargs)
        self.assertTrue(mock_get.called)
        self.assertTrue(ret_val)

    @mock.patch('requests.get')
    def test_download_ontology_fail(self, mock_get):
        mock_get.side_effect = KeyError(mock.Mock())
        ret_val = download_ontology(**self.download_ontology_kwargs)
        self.assertTrue(mock_get.called)
        self.assertFalse(ret_val)

    def test_get_owl_iri(self):
        iri = get_owl_iri('tests/resources/download_ontology/bfo.owl')
        self.assertEqual(iri, ('http://purl.obolibrary.org/obo/bfo/2019-08-26/bfo.owl', '2019-08-26'))

    def test_get_owl_iri_bad_input(self):
        iri = get_owl_iri('tests/resources/download_ontology/bfo_NO_VERSION_IRI.owl')
        self.assertEqual(("NA", "release"), iri)
