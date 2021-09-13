import botocore.exceptions  # type: ignore
import boto3  # type: ignore
from moto import mock_s3 # type: ignore
import os
import logging

def check_tracking(s3_bucket: str, s3_bucket_dir: str) -> bool:
    """
    Checks on existence of the tracking.yaml file on S3.
    :param s3_bucket: str ID of the bucket to upload to
    :param s3_bucket_dir: str of name of directory to create on S3
    :return: boolean returns True if tracking file exists, and False otherwise.
    """
    
    tracking_file_exists = False

    tracking_file_name = "tracking.yaml"

    client = boto3.client('s3')
    s3_path = os.path.join(s3_bucket_dir, tracking_file_name)
    print(f"Searching {s3_path} in {s3_bucket}")
    
    try:
        client.head_object(Bucket=s3_bucket, Key=s3_path)
        tracking_file_exists = True
    except botocore.exceptions.ClientError:
        tracking_file_exists = False
    except botocore.exceptions.NoCredentialsError:
        print("Could not find AWS S3 credentials, so could not check tracking.")
        tracking_file_exists = False

    return tracking_file_exists


def check_lock(s3_bucket: str, s3_bucket_dir: str) -> bool:
    """
    Checks on existence of a lock file on S3 to avoid concurrent runs.
    :param s3_bucket: str ID of the bucket to upload to
    :param s3_bucket_dir: str of name of directory to create on S3
    :return: boolean returns True if lock file exists, and False otherwise.
    """
    
    lock_exists = False

    lock_file_name = "lock"

    client = boto3.client('s3')
    s3_path = os.path.join(s3_bucket_dir, lock_file_name)
    
    try:
        client.head_object(Bucket=s3_bucket, Key=s3_path)
        lock_exists = True
    except botocore.exceptions.ClientError:
        lock_exists = False
    except botocore.exceptions.NoCredentialsError:
        print("Could not find AWS S3 credentials, so could not check for lock status.")
        lock_exists = True #It doesn't really exist but we can't continue anyway

    return lock_exists

def set_lock(s3_bucket: str, s3_bucket_dir: str) -> bool:
    """
    Creates a lock file on S3 to avoid concurrent runs.
    :param s3_bucket: str ID of the bucket to upload to
    :param s3_bucket_dir: str of name of directory to create on S3
    :return: boolean returns True if completed successfully, and False otherwise.
    """
    
    lock_created = False

    lock_file_name = "lock"

    client = boto3.client('s3')
    s3_path = os.path.join(s3_bucket_dir, lock_file_name)
    
    try:
        client.put_object(Bucket=s3_bucket, Key=s3_path)
        lock_created = True
    except botocore.exceptions.ClientError as e:
        print(f"Encountered error in setting lockfile on S3: {e}")
        lock_created = False
    except botocore.exceptions.NoCredentialsError:
        print("Could not find AWS S3 credentials, so could not create lock status.")
        lock_created = False #It doesn't really exist but we can't continue anyway

    return lock_created


def upload_dir_to_s3(local_directory: str, s3_bucket: str, s3_bucket_dir: str,
                     make_public=False) -> None:
    """
    Upload a local directory to a specified AWS S3 bucket.
    :param local_directory: str name of directory to upload
    :param s3_bucket: str ID of the bucket to upload to
    :param s3_bucket_dir: str of name of directory to create on S3
    """
    
    client = boto3.client('s3')
    for root, dirs, files in os.walk(local_directory):

        for filename in files:
            local_path = os.path.join(root, filename)

            # construct the full path
            relative_path = os.path.relpath(local_path, local_directory)
            s3_path = os.path.join(s3_bucket_dir, relative_path)

            print(f"Searching {s3_path} in {s3_bucket}")
            try:
                client.head_object(Bucket=s3_bucket, Key=s3_path)
                logging.warning("Existing file {s3_path} found on S3! Skipping.")
            except botocore.exceptions.ClientError:  # Exception abuse
                extra_args = {'ContentType': 'plain/text'}
                if filename == "index.html":
                    extra_args['ContentType'] = 'text/html'
                if make_public:
                    extra_args['ACL'] = 'public-read'
                logging.info(f"Uploading {s3_path}")
                client.upload_file(local_path, s3_bucket, s3_path, ExtraArgs=extra_args)
            except botocore.exceptions.ParamValidationError as e: #Raised when bucket ID is wrong
                print(e)

@mock_s3
def mock_check_tracking(s3_bucket: str, s3_bucket_dir: str) -> bool:
    """
    Mock checking on existence of the tracking.yaml file on S3.
    :param s3_bucket: str ID of the bucket to upload to
    :param s3_bucket_dir: str of name of directory to create on S3
    :return: boolean returns True if tracking file exists, and False otherwise.
    """
    
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    os.environ['AWS_SECURITY_TOKEN'] = 'test'
    os.environ['AWS_SESSION_TOKEN'] = 'test'

    tracking_file_exists = False

    tracking_file_name = "tracking.yaml"

    client = boto3.client('s3')
    s3_path = os.path.join(s3_bucket_dir, tracking_file_name)
    print(f"Searching {s3_path} in {s3_bucket}")
    
    print("Testing S3 only, so assuming tracking.yaml exists.")
    tracking_file_exists = True

    return tracking_file_exists

@mock_s3
def mock_check_lock(s3_bucket: str, s3_bucket_dir: str) -> bool:
    """
    Mock checking on existence of a lock file on S3 to avoid concurrent runs.
    :param s3_bucket: str ID of the bucket to upload to
    :param s3_bucket_dir: str of name of directory to create on S3
    :return: boolean returns True if lock file exists, and False otherwise.
    """
    
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    os.environ['AWS_SECURITY_TOKEN'] = 'test'
    os.environ['AWS_SESSION_TOKEN'] = 'test'

    lock_exists = False

    lock_file_name = "lock"

    client = boto3.client('s3')
    s3_path = os.path.join(s3_bucket_dir, lock_file_name)
    print("Testing S3 only, so assuming lock is not set.")
    
    try:
        client.head_object(Bucket=s3_bucket, Key=s3_path)
        lock_exists = True
    except botocore.exceptions.ClientError:
        lock_exists = False
    except botocore.exceptions.NoCredentialsError:
        print("Could not find AWS S3 credentials, so could not check for lock status.")
        lock_exists = True #It doesn't really exist but we can't continue anyway

    return lock_exists

@mock_s3
def mock_set_lock(s3_bucket: str, s3_bucket_dir: str) -> bool:
    """
    Mocks creating a lock file on S3 to avoid concurrent runs.
    :param s3_bucket: str ID of the bucket to upload to
    :param s3_bucket_dir: str of name of directory to create on S3
    :return: boolean returns True if completed successfully, and False otherwise.
    """
    
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    os.environ['AWS_SECURITY_TOKEN'] = 'test'
    os.environ['AWS_SESSION_TOKEN'] = 'test'

    lock_created = False

    lock_file_name = "lock"

    client = boto3.client('s3')
    s3_path = os.path.join(s3_bucket_dir, lock_file_name)
    
    # For mock purposes, we need to create the virtual bucket first. 
    try:
        client.create_bucket(Bucket=s3_bucket)
        client.put_object(Bucket=s3_bucket, Key=s3_path)
        lock_created = True
    except botocore.exceptions.ClientError as e:
        print(f"Encountered error in mock setting lockfile on S3: {e}")
        lock_created = False
    except botocore.exceptions.NoCredentialsError:
        print("Could not find AWS S3 credentials, so could not mock create lock status.")
        lock_created = False #It doesn't really exist but we can't continue anyway

    return lock_created


@mock_s3
def mock_upload_dir_to_s3(local_directory: str, s3_bucket: str, s3_bucket_dir: str,
                     make_public=False) -> None:
    """
    Mock the upload of a local directory to a specified AWS S3 bucket.
    Though this is a test, it is here so it may be more easily called through command options.
    :param local_directory: str name of directory to upload
    :param s3_bucket: str ID of the bucket to upload to
    :param s3_bucket_dir: str of name of directory to create on S3
    """
    
    print(f"Mock uploading to {s3_bucket_dir} on {s3_bucket}")
    
    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket=s3_bucket)
    
    upload_dir_to_s3(local_directory, s3_bucket, s3_bucket_dir, make_public)
    
    for bucket_object in conn.Bucket(s3_bucket).objects.all():
        print(bucket_object.key)

def upload_index_files(ontology_name: str, versioned_obo_path: str) -> None:
    """
    Checks the root, obo directory, and version directory,
    creating index.html where it does not exist.
    If index exists, update it if needed.
    :param ontology_name: str of ontology ID
    :param versioned_obo_path: str of directory containing this ontology version
    """

    # At present this will rebuild the root index at every transform/upload, which isn't great
    # so a different function or making this more generic may help
    
    ifilename = "index.html"
    
    index_head = """<!DOCTYPE html>
<html>
<head><title>Index of {this_dir}</title></head>
<body>
    <h2>Index of {this_dir}</h2>
    <hr>
    <ul>
        <li>
            <a href='../'>../</a>
        </li>
"""
    
    index_tail = """
    </ul>
</body>
</html>
"""

    check_dirs = [versioned_obo_path,
                    os.path.dirname(versioned_obo_path),
                    os.path.dirname(os.path.dirname(versioned_obo_path))]
    
    for dir in check_dirs:
        
        current_path = os.path.join(dir,ifilename)
        current_files = os.listdir(dir)
        
        #Even if index exists, just rebuild it
        with open(current_path, 'w') as ifile:
            ifile.write(index_head.format(this_dir=dir))
            for filename in current_files:
                if filename != 'index.html':
                    ifile.write(f"\t\t<li>\n\t\t\t<a href={filename}>{filename}</a>\n\t\t</li>\n")
            ifile.write(index_tail)
