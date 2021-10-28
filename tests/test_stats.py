import os
from unittest import TestCase, mock
from unittest.mock import Mock

from kg_obo.stats import retrieve_tracking, write_stats, get_file_metadata, \
                            get_graph_details, get_graph_stats
                            
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
    
    def test_write_stats(self):
        write_stats(self.stats)
        with open(self.stats_path) as statsfile:
            self.assertTrue(statsfile.read())

    @mock.patch('boto3.client')    
    def test_get_file_metadata(self, mock_boto):
        mlist = get_file_metadata(self.bucket, self.bucket_dir, 
                                    self.versions)
        self.assertTrue(mock_boto.called)

    # Incomplete while the function is incomplete
    def test_get_graph_details(self):
        glist = get_graph_details(self.bucket, self.bucket_dir, 
                                    self.versions)

    @mock.patch('boto3.client')
    @mock.patch('kg_obo.stats.retrieve_tracking')
    def test_get_graph_stats(self, mock_boto, mock_retrieve_tracking):
        get_graph_stats()
        self.assertTrue(mock_boto.called)

