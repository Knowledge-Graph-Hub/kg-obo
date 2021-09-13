from unittest import TestCase, mock
import botocore.exceptions

from kg_obo.upload import upload_dir_to_s3, mock_upload_dir_to_s3, \
                           check_tracking, mock_check_tracking, \
                           check_lock, mock_check_lock, \
                           set_lock, mock_set_lock

class TestUploadDirToS3(TestCase):

    def setUp(self) -> None:
        self.local_dir = "tests/resources/fake_upload_dir"
        self.bucket = "my_bucket"
        self.bucket_dir = "remote_dir"

    @mock.patch('boto3.client')
    def test_upload_dir_to_s3(self, mock_boto):
        upload_dir_to_s3(self.local_dir, self.bucket, self.bucket_dir)
        self.assertTrue(mock_boto.called)

    # This is essentially testing a test
    @mock.patch('boto3.client')
    def test_mock_upload_dir_to_s3(self, mock_boto):
        mock_upload_dir_to_s3(self.local_dir, self.bucket, self.bucket_dir)
        self.assertTrue(mock_boto.called)

    @mock.patch('boto3.client')
    def test_check_tracking(self, mock_boto):
        check_tracking(self.bucket, self.bucket_dir)
        self.assertTrue(mock_boto.called)

    #Test-of-test
    @mock.patch('boto3.client')
    def test_mock_check_tracking(self, mock_boto):
        mock_check_tracking(self.bucket, self.bucket_dir)
        self.assertTrue(mock_boto.called)

    @mock.patch('boto3.client')
    def test_check_lock(self, mock_boto):
        check_lock(self.bucket, self.bucket_dir)
        self.assertTrue(mock_boto.called)

    #Test-of-test
    @mock.patch('boto3.client')
    def test_mock_check_lock(self, mock_boto):
        mock_check_lock(self.bucket, self.bucket_dir)
        self.assertTrue(mock_boto.called)

    @mock.patch('boto3.client')
    def test_set_lock(self, mock_boto):
        set_lock(self.bucket, self.bucket_dir, unlock=False)
        self.assertTrue(mock_boto.called)

    #Test-of-test
    @mock.patch('boto3.client')
    def test_mock_set_lock(self, mock_boto):
        mock_set_lock(self.bucket, self.bucket_dir, unlock=False)
        self.assertTrue(mock_boto.called)
