from unittest import TestCase, mock
import botocore.exceptions

from kg_obo.upload import upload_dir_to_s3


class TestUploadDirToS3(TestCase):

    def setUp(self) -> None:
        self.local_dir = "tests/resources/fake_upload_dir"
        self.bucket = "my_bucket"
        self.bucket_dir = "remote_dir"

    @mock.patch('boto3.client')
    def test_upload_dir_to_s3(self, mock_boto):
        upload_dir_to_s3(self.local_dir, self.bucket, self.bucket_dir)
        self.assertTrue(mock_boto.called)
