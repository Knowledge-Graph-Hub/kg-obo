import logging
import tempfile
from unittest import TestCase, mock
from unittest.mock import Mock
from botocore.exceptions import ClientError

from kg_obo.transform import run_transform, kgx_transform, download_ontology, \
    get_owl_iri, retrieve_obofoundry_yaml


class TestRunTransform(TestCase):

    def setUp(self) -> None:
        self.kgx_transform_kwargs = {'input_file': ['foo'], 'input_format': 'tsv',
                                     'output_file': 'bar', 'output_format': 'tsv',
                                     'logger': logging.Logger}

        self.download_ontology_kwargs = {'url': 'https://some/url',
                                         'file': tempfile.NamedTemporaryFile().name,
                                         'logger': logging.getLogger("fake-log")}
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
           
    def test_retrieve_obofoundry_yaml_select(self):
        yaml_onto_list_filtered = retrieve_obofoundry_yaml(yaml_url="https://raw.githubusercontent.com/Knowledge-Graph-Hub/kg-obo/version-control/tests/resources/ontologies.yml", skip=[],get_only=[])
        self.assertEqual(yaml_onto_list_filtered, self.parsed_obo_yaml_sample)
        yaml_onto_list_filtered = retrieve_obofoundry_yaml(yaml_url="https://raw.githubusercontent.com/Knowledge-Graph-Hub/kg-obo/version-control/tests/resources/ontologies.yml", skip=["chebi"],get_only=[])
        self.assertEqual(yaml_onto_list_filtered[0], self.parsed_obo_yaml_sample[0])
        yaml_onto_list_filtered = retrieve_obofoundry_yaml(yaml_url="https://raw.githubusercontent.com/Knowledge-Graph-Hub/kg-obo/version-control/tests/resources/ontologies.yml", skip=[],get_only=["bfo"])
        self.assertEqual(yaml_onto_list_filtered[0], self.parsed_obo_yaml_sample[0])
