import logging
import tempfile
import pytest
import requests
from unittest import TestCase, mock
from unittest.mock import Mock
from botocore.exceptions import ClientError

from kg_obo.transform import run_transform, kgx_transform, download_ontology, \
    get_owl_iri, retrieve_obofoundry_yaml, transformed_obo_exists, track_obo_version, \
    delete_path, imports_requested, get_file_diff, get_file_length
from urllib.parse import quote

class TestRunTransform(TestCase):

    def setUp(self) -> None:
        self.kgx_transform_kwargs = {'input_file': ['foo'], 'input_format': 'tsv',
                                     'output_file': 'bar', 'output_format': 'tsv',
                                     'logger': logging.Logger}

        self.download_ontology_kwargs = {'url': 'https://some/url',
                                         'file': tempfile.NamedTemporaryFile().name,
                                         'logger': logging.getLogger("fake-log"),
                                         'no_dl_progress': 'False'}
        self.parsed_obo_yaml_sample = [{'activity_status': 'active',
            'browsers': [{'label': 'BioPortal', 'title': 'BioPortal Browser',
                         'url': 'http://bioportal.bioontology.org/ontologies/BFO?p=classes'
                         }],
            'contact': {'email': 'phismith@buffalo.edu', 'github': 'phismith',
                        'label': 'Barry Smith'},
            'depicted_by': 'https://avatars2.githubusercontent.com/u/12972134?v=3&s=200'
                ,
            'description': 'The upper level ontology upon which OBO Foundry ontologies are built.'
                ,
            'domain': 'upper',
            'homepage': 'http://ifomis.org/bfo/',
            'id': 'bfo',
            'in_foundry_order': 1,
            'layout': 'ontology_detail',
            'license': {'label': 'CC-BY',
                        'logo': 'http://mirrors.creativecommons.org/presskit/buttons/80x15/png/by.png'
                        , 'url': 'http://creativecommons.org/licenses/by/4.0/'
                        },
            'mailing_list': 'https://groups.google.com/forum/#!forum/bfo-discuss'
                ,
            'ontology_purl': 'http://purl.obolibrary.org/obo/bfo.owl',
            'products': [{'id': 'bfo.owl',
                         'ontology_purl': 'http://purl.obolibrary.org/obo/bfo.owl'
                         }, {'id': 'bfo.obo',
                         'ontology_purl': 'http://purl.obolibrary.org/obo/bfo.obo'
                         }],
            'repository': 'https://github.com/BFO-ontology/BFO',
            'review': {'date': 2016, 'document': {'label': 'PDF',
                       'link': 'https://drive.google.com/open?id=0B81h9ah4tAM_RnNTRUZnVGRyWXM'
                       }},
            'title': 'Basic Formal Ontology',
            'tracker': 'https://github.com/BFO-ontology/BFO/issues',
            'usages': [{'description': 'BFO is imported by multiple OBO ontologies to standardize upper level structure'
                       , 'type': 'owl_import', 'user': 'http://obofoundry.org'
                       }],
            }, {
            'activity_status': 'active',
            'alternatePrefix': 'ChEBI',
            'browsers': [{'label': 'CHEBI', 'title': 'EBI CHEBI Browser',
                         'url': 'http://www.ebi.ac.uk/chebi/chebiOntology.do?treeView=true&chebiId=CHEBI:24431#graphView'
                         }],
            'build': {'infallible': 1, 'method': 'obo2owl',
                      'source_url': 'ftp://ftp.ebi.ac.uk/pub/databases/chebi/ontology/chebi.obo'
                      },
            'contact': {'email': 'amalik@ebi.ac.uk', 'github': 'amalik01',
                        'label': 'Adnan Malik'},
            'depicted_by': 'https://www.ebi.ac.uk/chebi/images/ChEBI_logo.png',
            'description': "A structured classification of molecular entities of biological interest focusing on 'small' chemical compounds."
                ,
            'domain': 'biochemistry',
            'homepage': 'http://www.ebi.ac.uk/chebi',
            'id': 'chebi',
            'in_foundry_order': 1,
            'layout': 'ontology_detail',
            'license': {'label': 'CC-BY 4.0',
                        'logo': 'http://mirrors.creativecommons.org/presskit/buttons/80x15/png/by.png'
                        , 'url': 'https://creativecommons.org/licenses/by/4.0/'
                        },
            'ontology_purl': 'http://purl.obolibrary.org/obo/chebi.owl',
            'page': 'http://www.ebi.ac.uk/chebi/init.do?toolBarForward=userManual'
                ,
            'products': [{'id': 'chebi.owl',
                         'ontology_purl': 'http://purl.obolibrary.org/obo/chebi.owl'
                         }, {'id': 'chebi.obo',
                         'ontology_purl': 'http://purl.obolibrary.org/obo/chebi.obo'
                         }, {'id': 'chebi.owl.gz',
                         'ontology_purl': 'http://purl.obolibrary.org/obo/chebi.owl.gz'
                         , 'title': 'chebi, compressed owl'},
                         {'id': 'chebi/chebi_lite.obo',
                         'ontology_purl': 'http://purl.obolibrary.org/obo/chebi/chebi_lite.obo'
                         , 'title': 'chebi_lite, no syns or xrefs'},
                         {'id': 'chebi/chebi_core.obo',
                         'ontology_purl': 'http://purl.obolibrary.org/obo/chebi/chebi_core.obo'
                         , 'title': 'chebi_core, no xrefs'}],
            'publications': [{'id': 'http://europepmc.org/article/MED/26467479'
                             ,
                             'title': 'ChEBI in 2016: Improved services and an expanding collection of metabolites.'
                             }],
            'repository': 'https://github.com/ebi-chebi/ChEBI',
            'review': {'date': 2010},
            'title': 'Chemical Entities of Biological Interest',
            'tracker': 'https://github.com/ebi-chebi/ChEBI/issues',
            'twitter': 'chebit',
            'usages': [{'description': 'Rhea uses CHEBI to annotate reaction participants'
                       ,
                       'examples': [{'description': 'Query for all usages of CHEBI:29748 (chorismate)'
                       ,
                       'url': 'https://www.rhea-db.org/searchresults?q=CHEBI:29748'
                       }], 'user': 'https://www.rhea-db.org/'},
                       {'description': 'ZFIN uses CHEBI to annotate experiments'
                       ,
                       'examples': [{'description': 'A curated zebrafish experiment involving exposure to (5Z,8Z,14Z)-11,12-dihydroxyicosatrienoic acid (CHEBI:63969)'
                       ,
                       'url': 'http://zfin.org/action/expression/experiment?id=ZDB-EXP-190627-10'
                       }], 'user': 'http://zfin.org'}],
            }]

    @mock.patch('requests.get')
    @mock.patch('kg_obo.transform.retrieve_obofoundry_yaml')
    @mock.patch('kg_obo.obolibrary_utils.base_url_if_exists')
    @mock.patch('kg_obo.transform.get_owl_iri', return_value=('http://purl.obolibrary.org/obo/bfo/2019-08-26/bfo.owl', '2019-08-26'))
    @mock.patch('kgx.cli.transform')
    def test_run_transform(self, mock_kgx_transform, mock_get_owl_iri, mock_base_url,
                           mock_retrieve_obofoundry_yaml, mock_get): 
        mock_retrieve_obofoundry_yaml.return_value = [{'id': 'bfo'}]

        # Test with s3_test option on
        with tempfile.TemporaryDirectory() as td:
            run_transform(log_dir=td,s3_test=True)
            self.assertTrue(mock_get.called)
            self.assertTrue(mock_base_url.called)
            self.assertTrue(mock_get_owl_iri.called)
            self.assertTrue(mock_retrieve_obofoundry_yaml.called)
            self.assertTrue(mock_kgx_transform.called)

        # Test with s3_test option off
        with tempfile.TemporaryDirectory() as td:
            run_transform(log_dir=td,s3_test=False)
            self.assertTrue(mock_get.called)
            self.assertTrue(mock_base_url.called)
            self.assertTrue(mock_get_owl_iri.called)
            self.assertTrue(mock_retrieve_obofoundry_yaml.called)
            self.assertTrue(mock_kgx_transform.called)

        # Test if error raised when ROBOT not available
        # though we also want to continue without it
        with tempfile.TemporaryDirectory() as td:
            run_transform(log_dir=td,s3_test=True,robot_path="wrong")
            self.assertRaises(ValueError)
            self.assertTrue(mock_kgx_transform.called)

        # test that we don't run transform if download of ontology fails
        with mock.patch('kg_obo.transform.download_ontology', return_value=False),\
                tempfile.TemporaryDirectory() as td:
            mock_kgx_transform.reset_mock()
            run_transform(log_dir=td,s3_test=True)
            self.assertFalse(mock_kgx_transform.called)
        
        # also don't run transform if lockfile not settable
        with mock.patch('kg_obo.upload.mock_set_lock', return_value=False),\
                tempfile.TemporaryDirectory() as td:
            mock_kgx_transform.reset_mock()
            run_transform(log_dir=td,s3_test=True)
            self.assertFalse(mock_kgx_transform.called)
        with mock.patch('kg_obo.upload.set_lock', return_value=False),\
                tempfile.TemporaryDirectory() as td:
            mock_kgx_transform.reset_mock()
            run_transform(log_dir=td,s3_test=False)
            self.assertFalse(mock_kgx_transform.called)

        # also don't run transform if tracking file not accessible
        with mock.patch('kg_obo.upload.mock_check_tracking', return_value=False),\
                tempfile.TemporaryDirectory() as td:
            mock_kgx_transform.reset_mock()
            run_transform(log_dir=td,s3_test=True)
            self.assertFalse(mock_kgx_transform.called)
        with mock.patch('kg_obo.upload.check_tracking', return_value=False),\
                tempfile.TemporaryDirectory() as td:
            mock_kgx_transform.reset_mock()
            run_transform(log_dir=td,s3_test=False)
            self.assertFalse(mock_kgx_transform.called)

        # Test for refreshing the index 
        with tempfile.TemporaryDirectory() as td:
            run_transform(log_dir=td,s3_test=False, force_index_refresh=True)
            self.assertTrue(mock_retrieve_obofoundry_yaml.called)

        # Test if we need to do full ROBOT relax -> merge -> convert
        with tempfile.TemporaryDirectory() as td:
            run_transform(log_dir=td,s3_test=True,get_only=['apollo_sv'])
            self.assertTrue(mock_kgx_transform.called)

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
        ret_val = download_ontology(**self.download_ontology_kwargs, header_only=False)
        self.assertTrue(mock_get.called)
        self.assertTrue(ret_val)

    @mock.patch('requests.get')
    def test_download_ontology_headeronly(self, mock_get):
        ret_val = download_ontology(**self.download_ontology_kwargs, header_only=True)
        self.assertTrue(mock_get.called)
        self.assertTrue(ret_val)

    @mock.patch('requests.get')
    def test_download_ontology_fail(self, mock_get):
        mock_get.side_effect = KeyError(mock.Mock())
        ret_val = download_ontology(**self.download_ontology_kwargs, header_only=False)
        self.assertTrue(mock_get.called)
        self.assertFalse(ret_val)

    @mock.patch('requests.get')
    def test_download_ontology_connectionerror(self, mock_get):
        mock_get.side_effect = requests.ConnectionError(mock.Mock())
        ret_val = download_ontology(**self.download_ontology_kwargs, header_only=False)
        self.assertTrue(mock_get.called)
        self.assertFalse(ret_val)

    def test_get_owl_iri(self):
        iri = get_owl_iri('tests/resources/download_ontology/bfo.owl')
        self.assertEqual(iri, ('http://purl.obolibrary.org/obo/bfo/2019-08-26/bfo.owl', '2019-08-26'))
        with pytest.raises(Exception):
            iri = get_owl_iri('')

    def test_get_owl_iri_for_aro(self):
        iri = get_owl_iri('tests/resources/download_ontology/aro_SNIPPET.owl')
        self.assertEqual(('http://purl.obolibrary.org/obo/antibiotic_resistance.owl', ('05_07_2021 15_21')), iri)

    def test_get_owl_iri_for_go(self):
        iri = get_owl_iri('tests/resources/download_ontology/go_SNIPPET.owl')
        self.assertEqual(('http://purl.obolibrary.org/obo/go/releases/2021-09-01/go-base.owl', '2021-09-01'), iri)

    def test_get_owl_iri_for_micro(self):
        iri = get_owl_iri('tests/resources/download_ontology/micro_SNIPPET.owl')
        self.assertEqual(('&obo;MicrO.owl', '72c3cb2dfd015a0817680fe07261322c'), iri)

    def test_get_owl_iri_bad_input(self):
        iri = get_owl_iri('tests/resources/download_ontology/bfo_NO_VERSION_IRI.owl')
        self.assertEqual(("http://purl.obolibrary.org/obo/bfo.owl", "no_version"), iri)

    def test_imports_requested(self):
        imports = imports_requested('tests/resources/download_ontology/upheno_SNIPPET.owl')
        self.assertEqual(imports, ["&obo;upheno/metazoa.owl"])
    
    def test_retrieve_obofoundry_yaml_select(self):
        yaml_onto_list_filtered = retrieve_obofoundry_yaml(yaml_url="https://raw.githubusercontent.com/Knowledge-Graph-Hub/kg-obo/main/tests/resources/ontologies.yml", skip=[],get_only=[])
        self.assertEqual(yaml_onto_list_filtered, self.parsed_obo_yaml_sample)
        yaml_onto_list_filtered = retrieve_obofoundry_yaml(yaml_url="https://raw.githubusercontent.com/Knowledge-Graph-Hub/kg-obo/main/tests/resources/ontologies.yml", skip=["chebi"],get_only=[])
        self.assertEqual(yaml_onto_list_filtered[0], self.parsed_obo_yaml_sample[0])
        yaml_onto_list_filtered = retrieve_obofoundry_yaml(yaml_url="https://raw.githubusercontent.com/Knowledge-Graph-Hub/kg-obo/main/tests/resources/ontologies.yml", skip=[],get_only=["bfo"])
        self.assertEqual(yaml_onto_list_filtered[0], self.parsed_obo_yaml_sample[0])
        with pytest.raises(Exception):
            yaml_onto_list_filtered = retrieve_obofoundry_yaml(yaml_url="")

    @mock.patch('boto3.client')
    def test_track_obo_version(self, mock_boto):
        track_path = "tests/resources/tracking.yaml"
        # Test adding to tracking when no version exists
        name = "bfo"
        iri = "iri-1"
        version = "version-1"
        bucket = "test"
        track_obo_version(name, iri, version, bucket,
                          track_file_local_path=track_path,
                          track_file_remote_path=track_path)
        self.assertTrue(mock_boto.called)
        # Now test adding to tracking when old version exists
        iri = "iri-2"
        version = "version-2"
        track_obo_version(name, iri, version, bucket,
                          track_file_local_path=track_path,
                          track_file_remote_path=track_path)
        self.assertTrue(mock_boto.called)

    @mock.patch('boto3.client')
    def test_transformed_obo_exists(self, mock_boto):
        track_path = "tests/resources/tracking.yaml"
        # First track obo existence
        name = "bfo"
        iri = "iri_old"
        version = "version_old"
        bucket = "test"
        track_obo_version(name, iri, version, bucket,
                          track_file_local_path=track_path,
                          track_file_remote_path=track_path)
        # Now see if it exits in the tracking
        transformed_obo_exists(name, iri,
                          tracking_file_local_path=track_path,
                          tracking_file_remote_path=track_path)
        self.assertTrue(mock_boto.called)

        iri = "iri_new"
        version = "version_new"
        track_obo_version(name, iri, version, bucket,
                          track_file_local_path=track_path,
                          track_file_remote_path=track_path)
        # Now see if it exits in the tracking, again
        iri = "iri_old"
        transformed_obo_exists(name, iri,
                          tracking_file_local_path=track_path,
                          tracking_file_remote_path=track_path)
        self.assertTrue(mock_boto.called)

    def test_delete_path(self):
        data_path = "tests/resources/fake_upload_dir/"
        self.assertTrue(delete_path(data_path, omit=[]))
        data_path = "tests/resources/a_dir_that_definitely_does_not_exist/"
        self.assertFalse(delete_path(data_path, omit=[]))

    def test_get_file_diff(self):
        diff = get_file_diff('tests/resources/download_ontology/go_SNIPPET.owl',
                            'tests/resources/download_ontology/go_SNIPPET.owl')
        self.assertEqual("No difference", diff)
        diff = get_file_diff('tests/resources/download_ontology/go_SNIPPET.owl',
                            'tests/resources/download_ontology/aro_SNIPPET.owl')
        self.assertNotEqual("No difference", diff)

    def test_get_file_length(self):
        count = get_file_length('tests/resources/download_ontology/go_SNIPPET.owl')
        self.assertEqual(24, count)
