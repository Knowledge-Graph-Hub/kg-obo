from unittest import TestCase, mock
from unittest.mock import Mock

from botocore.exceptions import ClientError

from kg_obo import upload_dir_to_s3


class TestUploadDirToS3(TestCase):

    def setUp(self) -> None:
        pass

    @mock.patch('boto3.client')
    def test_upload_dir_to_s3(self, mock_boto):
        local_dir = "tests/resources/fake_upload_dir"
        bucket = "my_bucket"
        bucket_dir = "remote_dir"
        upload_dir_to_s3(local_dir, bucket, bucket_dir)
        self.assertTrue(mock_boto.called)

