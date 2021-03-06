from unittest import TestCase, mock
import botocore.exceptions

from kg_obo.upload import upload_dir_to_s3, mock_upload_dir_to_s3, \
                            check_tracking, mock_check_tracking, \
                            check_lock, mock_check_lock, \
                            set_lock, mock_set_lock, \
                            update_index_files, mock_update_index_files, \
                            verify_uploads, upload_reports

class TestUploadDirToS3(TestCase):

    def setUp(self) -> None:
        self.local_dir = "tests/resources/fake_upload_dir"
        self.download_ontology_dir = "tests/resources/download_ontology"
        self.bucket = "my_bucket"
        self.bucket_dir = "remote_dir"
        self.data_dir = "data"
        self.filelist = ['tsv_transform.log', 'obo_kgx.json', 
                        'json_transform.log', 'obo_kgx_tsv.tar.gz']
        self.name = "obo"

    @mock.patch('boto3.client')
    def test_upload_dir_to_s3(self, mock_boto):
        filelist = upload_dir_to_s3(self.local_dir, self.bucket, self.bucket_dir)
        self.assertTrue(mock_boto.called)
        self.assertEqual(filelist, []) #Will be true because the directory is empty

    # This is essentially testing a test
    @mock.patch('boto3.client')
    def test_mock_upload_dir_to_s3(self, mock_boto):
        filelist = mock_upload_dir_to_s3(self.local_dir, self.bucket, self.bucket_dir)
        self.assertTrue(mock_boto.called)
        self.assertEqual(filelist, []) #Will be true because the directory is empty

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

    @mock.patch('boto3.client')
    def test_update_index_files(self, mock_boto):
        update_index_files(self.bucket, self.bucket_dir, self.data_dir,
                            update_root=False)
        self.assertTrue(mock_boto.called)
        update_index_files(self.bucket, self.bucket_dir, self.data_dir,
                            update_root=True)
        self.assertTrue(mock_boto.called)

    #Test-of-test
    @mock.patch('boto3.client')
    def test_mock_update_index_files(self, mock_boto):
        mock_update_index_files(self.bucket, self.bucket_dir, self.data_dir,
                            update_root=False)
        self.assertTrue(mock_boto.called)
        mock_update_index_files(self.bucket, self.bucket_dir, self.data_dir,
                            update_root=True)
        self.assertTrue(mock_boto.called)

    def test_verify_uploads(self):
        self.assertTrue(verify_uploads(self.filelist, self.name))
        wrong_filelist = ['tsv_transform.log', 'obo_kgx.json.gz', 
                        'json_transform.log', 'obo_tsv.tar.gz']
        self.assertFalse(verify_uploads(wrong_filelist, self.name))

    @mock.patch('boto3.client')
    def test_upload_reports(self, mock_boto):
        upload_reports(self.bucket)
        self.assertTrue(mock_boto.called)
