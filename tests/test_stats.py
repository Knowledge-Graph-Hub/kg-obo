import os
from unittest import TestCase, mock
from unittest.mock import Mock

from kg_obo.stats import retrieve_tracking, write_stats, get_clean_file_metadata, \
                            get_graph_details, get_file_list, get_all_stats, \
                            decompress_graph
                            
class TestStats(TestCase):

    def setUp(self) -> None:
        self.bucket = "my_bucket"
        self.bucket_dir = "remote_dir"
        self.stats_path = "stats/stats.tsv"
        self.stats = [{"Test1": "A", "Test2": "B"},
                        {"Test1": "C", "Test2": "D"}]
        self.versions = [{"Name": "Foo", "Version": "1"},
                        {"Name": "Bar", "Version": "2"}]

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

    #This mock bucket is empty, so function will exit.
    @mock.patch('boto3.client')    
    def test_get_clean_file_metadata(self, mock_boto):
        with self.assertRaises(SystemExit) as e:
            mlist = get_clean_file_metadata(self.bucket, self.bucket_dir, 
                                    self.versions)
            self.assertTrue(len(mlist)==0) 
            self.assertTrue(mock_boto.called)
            assert e.type == SystemExit

    @mock.patch('boto3.client')  
    def test_get_graph_details(self, mock_boto):
        glist = get_graph_details(self.bucket, self.bucket_dir, 
                                    self.versions)
        self.assertTrue(mock_boto.called)

    @mock.patch('boto3.client')   
    def test_get_file_list(self, mock_boto):
        flist = get_file_list(self.bucket, self.bucket_dir, 
                                    self.versions)
        self.assertTrue(len(flist)==0) #This mock bucket is empty.
        self.assertTrue(mock_boto.called)

    def test_decompress_graph(self):
        tar_path = "./tests/resources/download_ontology/test_kgx_tsv.tar.gz"
        edge_path = "./tests/resources/download_ontology/test_kgx_tsv_edges.tsv"
        decompress_graph("test", tar_path)
        with open(edge_path) as edgefile:
            self.assertTrue(edgefile.read())

    #Without further mocking, buckets will look empty
    #so functions will quit early.
    @mock.patch('boto3.client')
    @mock.patch('kg_obo.stats.retrieve_tracking')
    def test_get_all_stats(self, mock_boto, mock_retrieve_tracking):
        with self.assertRaises(SystemExit) as e:
            get_all_stats(save_local=True)
            assert e.type == SystemExit
        with self.assertRaises(SystemExit) as e:
            get_all_stats(skip=["bfo"])
            assert e.type == SystemExit
        with self.assertRaises(SystemExit) as e:
            get_all_stats(get_only=["bfo"])
            assert e.type == SystemExit


