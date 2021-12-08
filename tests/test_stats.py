import os
from unittest import TestCase, mock
from unittest.mock import Mock
import datetime
from dateutil.tz import tzutc

from kg_obo.stats import retrieve_tracking, robot_axiom_validations, write_stats, get_clean_file_metadata, \
                            get_graph_details, get_file_list, get_all_stats, \
                            decompress_graph, validate_version_name, \
                            compare_versions, cleanup, parse_robot_metrics

from kg_obo.robot_utils import initialize_robot
                            
class TestStats(TestCase):

    def setUp(self) -> None:
        self.bucket = "my_bucket"
        self.bucket_dir = "remote_dir"
        self.stats_path = "stats/stats.tsv"
        self.stats = [{"Test1": "A", "Test2": "B"},
                        {"Test1": "C", "Test2": "D"}]
        self.entry = {'Name': 'bfo', 
                        'Version': '2019-08-26', 
                        'Format': 'TSV', 'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()),
                        'Size': 17251, 
                        'Nodes': 73, 
                        'Edges': 116, 
                        'ConnectedComponents': (10, 1, 49), 
                        'Singletons': 7, 
                        'MaxNodeDegree': 47, 
                        'MeanNodeDegree': '3.18'}
        self.versions = [{'Name': 'bfo', 
                        'Version': '2019-08-26',
                        'Format': 'TSV', 
                        'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()), 
                        'Size': 17251, 
                        'Nodes': 73, 
                        'Edges': 116, 
                        'ConnectedComponents': (10, 1, 49), 
                        'Singletons': 7, 
                        'MaxNodeDegree': 47, 
                        'MeanNodeDegree': '3.18'},
                        {'Name': 'bfo', 
                        'Version': '2019-08-26', 
                        'Format': 'JSON', 
                        'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()),
                        'Size': 114355, 
                        'Nodes': 73, 
                        'Edges': 116, 
                        'ConnectedComponents': (10, 1, 49), 
                        'Singletons': 7, 
                        'MaxNodeDegree': 47, 
                        'MeanNodeDegree': '3.18'}]
        self.multiversions = [{'Name': 'bfo', 
                        'Version': '2019-08-26',
                        'Format': 'TSV', 
                        'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()), 
                        'Size': 17251, 
                        'Nodes': 73, 
                        'Edges': 116, 
                        'ConnectedComponents': (10, 1, 49), 
                        'Singletons': 7, 
                        'MaxNodeDegree': 47, 
                        'MeanNodeDegree': '3.18'},
                        {'Name': 'bfo', 
                        'Version': '2019-08-26', 
                        'Format': 'TSV', 
                        'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()),
                        'Size': 17251, 
                        'Nodes': 73, 
                        'Edges': 116, 
                        'ConnectedComponents': (10, 1, 49), 
                        'Singletons': 7, 
                        'MaxNodeDegree': 47, 
                        'MeanNodeDegree': '3.18'},
                        {'Name': 'bfo', 
                        'Version': '2020-08-26', 
                        'Format': 'TSV', 
                        'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()),
                        'Size': 300, 
                        'Nodes': 73, 
                        'Edges': 116, 
                        'ConnectedComponents': (10, 1, 49), 
                        'Singletons': 7, 
                        'MaxNodeDegree': 47, 
                        'MeanNodeDegree': '3.18'}]

    @mock.patch('boto3.client')
    def test_retrieve_tracking(self, mock_boto):
        vlist = retrieve_tracking(self.bucket, self.bucket_dir,
                                    "./tests/resources/tracking.yaml")
        self.assertTrue(len(vlist)>0)
        self.assertTrue(mock_boto.called)
        vlist = retrieve_tracking(self.bucket, self.bucket_dir,
                                    "./tests/resources/tracking.yaml",
                                    skip=["bfo"])
        self.assertTrue(mock_boto.called)
        vlist = retrieve_tracking(self.bucket, self.bucket_dir,
                                    "./tests/resources/tracking.yaml",
                                    get_only=["bfo"])
        self.assertTrue(mock_boto.called)

    def test_write_stats(self):
        write_stats(self.stats,self.stats_path)
        with open(self.stats_path) as statsfile:
            self.assertTrue(statsfile.read())

    @mock.patch('kg_obo.stats.get_file_list', 
                return_value={'kg-obo/bfo/2019-08-26/bfo_kgx.json': {'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()),
                            'Size': 114355,
                            'Format': 'JSON'},
                            'kg-obo/bfo/2019-08-26/bfo_kgx_tsv.tar.gz': {'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()),
                            'Size': 17251, 
                            'Format': 'TSV'}})
    def test_get_clean_file_metadata(self, mock_get_file_list):
        mlist = get_clean_file_metadata(self.bucket, self.bucket_dir, 
                                    self.versions)
        self.assertTrue(mock_get_file_list.called)

    def test_decompress_graph(self):
        tar_path = "./tests/resources/download_ontology/graph.tar.gz"
        edge_path = "./tests/resources/download_ontology/bfo_kgx_tsv_edges.tsv"
        decompress_graph("bfo", tar_path)
        with open(edge_path) as edgefile:
            self.assertTrue(edgefile.read())

    @mock.patch('boto3.client')  
    @mock.patch('kg_obo.stats.get_file_list', 
                return_value={'kg-obo/bfo/2019-08-26/bfo_kgx.json': {'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()),
                            'Size': 114355,
                            'Format': 'JSON'},
                            'kg-obo/bfo/2019-08-26/bfo_kgx_tsv.tar.gz': {'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()),
                            'Size': 17251, 
                            'Format': 'TSV'}})
    @mock.patch('kg_obo.stats.decompress_graph',
                return_value=('tests/resources/download_ontology/bfo_kgx_tsv_edges.tsv',
                                'tests/resources/download_ontology/bfo_kgx_tsv_nodes.tsv'))
    def test_get_graph_details(self, mock_boto, mock_get_file_list,
                                mock_decompress_graph):
        glist = get_graph_details(self.bucket, self.bucket_dir, 
                                    self.versions)
        self.assertTrue(mock_boto.called)
        self.assertTrue(mock_get_file_list.called)
        self.assertTrue(mock_decompress_graph.called)

    @mock.patch('boto3.client')   
    def test_get_file_list(self, mock_boto):
        flist = get_file_list(self.bucket, self.bucket_dir, 
                                    self.versions)
        self.assertTrue(len(flist)==0) #This mock bucket is empty.
        self.assertTrue(mock_boto.called)

    def test_compare_versions(self):
        compare = compare_versions(self.entry, self.versions)
        self.assertEqual(compare,{'Large Difference in Edge Count': [],
                                'Large Difference in Node Count': [],
                                'Large Difference in Size': []})
        compare = compare_versions(self.entry, self.multiversions)
        self.assertNotEqual(compare,{'Large Difference in Edge Count': [],
                                'Large Difference in Node Count': [],
                                'Large Difference in Size': []})

    def test_cleanup(self):
        test_data_dir = "./data/testdir/"
        os.makedirs(test_data_dir)
        cleanup("testdir")
        self.assertFalse(os.path.isdir(test_data_dir))

    def test_validiate_version_name(self):
        good_version = "2020-10-15"
        bad_version = "release"
        self.assertTrue(validate_version_name(good_version))
        self.assertFalse(validate_version_name(bad_version))

    @mock.patch('boto3.client') 
    def test_robot_axiom_validations(self, mock_boto):
        robot_path = os.path.join(os.getcwd(),"robot")
        robot_params = initialize_robot(robot_path)
        robot_env = robot_params[1]
        robot_axiom_validations(self.bucket, self.bucket_dir,
                                robot_path, robot_env,
                                self.versions)
        self.assertTrue(mock_boto.called)
    
    def test_parse_robot_metrics(self):
        inpath = "./tests/resources/test-owl-profile-validation.tsv"
        wanted_metrics = ['constructs', 'rule_count']
        metrics = parse_robot_metrics(inpath, wanted_metrics)
        self.assertEqual(metrics, {'constructs':['I','O','Q','R','S'],
                                    'rule_count':['0']})

    @mock.patch('boto3.client') 
    @mock.patch('kg_obo.upload.check_tracking', return_value = True)
    @mock.patch('kg_obo.stats.retrieve_tracking', 
                return_value = [{'Name': 'bfo',
                            'Version': '2019-08-26',
                            'Format': 'TSV'},
                            {'Name': 'bfo',
                            'Version': '2019-08-26',
                            'Format': 'JSON'}])
    @mock.patch('kg_obo.stats.get_clean_file_metadata', 
                return_value={'bfo': {'2019-08-26': {'JSON': {'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()),
                             'Size': 114355},
                            'TSV': {'LastModified': datetime.datetime(2021, 10, 1, 20, 10, 9, tzinfo=tzutc()),
                             'Size': 17251}}}})
    @mock.patch('kg_obo.stats.get_graph_details', 
                return_value={'bfo': {'2019-08-26': {'Nodes': 73,
                            'Edges': 116,
                            'ConnectedComponents': (10, 1, 49),
                            'Singletons': 7, 
                            'MaxNodeDegree': 47, 
                            'MeanNodeDegree': '3.18'}}})
    def test_get_all_stats(self, mock_boto,
                            mock_check_tracking,
                            mock_retrieve_tracking,
                            mock_get_clean_file_metadata,
                            mock_get_graph_details):
        get_all_stats()
        self.assertTrue(mock_boto.called)
        self.assertTrue(mock_check_tracking.called)
        self.assertTrue(mock_retrieve_tracking.called)
        self.assertTrue(mock_get_clean_file_metadata.called)
        self.assertTrue(mock_get_graph_details.called)
        get_all_stats(get_only=["bfo"])
        self.assertTrue(mock_boto.called)
        self.assertTrue(mock_check_tracking.called)
        self.assertTrue(mock_retrieve_tracking.called)
        self.assertTrue(mock_get_clean_file_metadata.called)
        self.assertTrue(mock_get_graph_details.called)

            


