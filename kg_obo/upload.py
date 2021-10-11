import botocore.exceptions  # type: ignore
import boto3  # type: ignore
from moto import mock_s3 # type: ignore
import os
import logging
from time import time

IFILENAME = "index.html"

def check_tracking(s3_bucket: str, s3_bucket_dir: str) -> bool:
    """
    Checks on existence of the tracking.yaml file on S3.
    :param s3_bucket: str ID of the bucket to upload to
    :param s3_bucket_dir: str of name of directory to create on S3
    :return: boolean returns True if tracking file exists, and False otherwise.
    """

    tracking_file_exists = False

    client = boto3.client('s3')
    s3_path = s3_bucket_dir
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

    client = boto3.client('s3')
    s3_path = s3_bucket_dir

    try:
        client.head_object(Bucket=s3_bucket, Key=s3_path)
        lock_exists = True
    except botocore.exceptions.ClientError:
        lock_exists = False
    except botocore.exceptions.NoCredentialsError:
        print("Could not find AWS S3 credentials, so could not check for lock status.")
        lock_exists = True #It doesn't really exist but we can't continue anyway

    return lock_exists

def set_lock(s3_bucket: str, s3_bucket_dir: str, unlock: bool) -> bool:
    """
    Creates a lock file on S3 to avoid concurrent runs.
    :param s3_bucket: str ID of the bucket to upload to
    :param s3_bucket_dir: str of name of directory to create on S3
    :return: boolean returns True if completed successfully, and False otherwise.
    """

    lock_created = False

    client = boto3.client('s3')
    s3_path = s3_bucket_dir

    try:
        if not unlock:
            print(f"creating lock file s3_bucket:{s3_bucket}, s3_path:{s3_path}")
            client.put_object(Bucket=s3_bucket, Key=s3_path)
            lock_created = True
        else:
            print(f"deleting lock file s3_bucket:{s3_bucket}, s3_path:{s3_path}")
            client.delete_object(Bucket=s3_bucket, Key=s3_path)
            lock_created = True
    except botocore.exceptions.ClientError as e:
        print(f"Encountered error in setting lockfile on S3: {e}")
        lock_created = False
    except botocore.exceptions.NoCredentialsError:
        print("Could not find AWS S3 credentials, so could not set lock status.")
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
                logging.warning(f"Existing file {s3_path} found on S3! Skipping.")
            except botocore.exceptions.ClientError:  # Exception abuse
                extra_args = {'ContentType': 'plain/text'}
                if filename == "index.html":
                    continue #Index is uploaded separately
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

    client = boto3.client('s3')
    s3_path = s3_bucket_dir
    print(f"Mock searching {s3_path} in {s3_bucket}")

    # Create simulated bucket and track file first
    client.create_bucket(Bucket=s3_bucket)
    client.put_object(Bucket=s3_bucket, Key=s3_path)

    try:
        client.head_object(Bucket=s3_bucket, Key=s3_path)
        tracking_file_exists = True
    except botocore.exceptions.ClientError:
        tracking_file_exists = False
    except botocore.exceptions.NoCredentialsError:
        print("Could not find AWS S3 credentials, so could not check tracking.")
        tracking_file_exists = False

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

    client = boto3.client('s3')
    s3_path = s3_bucket_dir
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
def mock_set_lock(s3_bucket: str, s3_bucket_dir: str, unlock: bool) -> bool:
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

    client = boto3.client('s3')
    s3_path = s3_bucket_dir

    # For mock purposes, we need to create the virtual bucket first.
    try:
        if not unlock:
            client.create_bucket(Bucket=s3_bucket)
            client.put_object(Bucket=s3_bucket, Key=s3_path)
            lock_created = True
        else:
            client.create_bucket(Bucket=s3_bucket)
            client.put_object(Bucket=s3_bucket, Key=s3_path)
            client.delete_object(Bucket=s3_bucket, Key=s3_path)
            lock_created = True
    except botocore.exceptions.ClientError as e:
        print(f"Encountered error in mock setting lockfile on S3: {e}")
        lock_created = False
    except botocore.exceptions.NoCredentialsError:
        print("Could not find AWS S3 credentials, so could not mock set lock status.")
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


def update_index_files(bucket: str, remote_path: str, data_dir: str, update_root=False, existing_client=None) -> bool:
    """
    Checks a specified remote path on the S3 bucket, 
    creating index.html where it does not exist.
    If index exists, update it if needed.
    This index reflects both newly-added AND extant files on the specified bucket,
    as it should be called after uploading new files
    (but may also be called on its own to rebuild index.html).
    :param bucket: str of S3 bucket
    :param remote_path: str of path to upload to
    :param data_dir: str of the data directory, where the index will temporarily be saved
    :param update_root: bool, True to update root index, which performs extra dead link checks
    :param existing_client: an object of class 'botocore.client.s3', for mocking persistence
    :return: bool returns True if all index files created successfully
    """

    success = False

    if existing_client:
        client = existing_client
    else:
        client = boto3.client('s3')

    ifile_local_path = os.path.join(data_dir,IFILENAME)
    ifile_remote_path = os.path.join(remote_path,IFILENAME)

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

    index_link = "\t\t<li>\n\t\t\t<a href={link}>{link}</a>\n\t\t</li>\n"
    
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    # Get list of remote files
    remote_files = []
    try:
        remote_contents = client.list_objects(Bucket=bucket, Prefix=remote_path+"/")['Contents']
        for key in remote_contents:
            if os.path.basename(key['Key']) not in [IFILENAME,"tracking.yaml"]:
                remote_files.append(key['Key'])
        print(f"Found existing contents at {remote_path}: {remote_files}")
    except KeyError:
        print(f"Found no existing contents at {remote_path}")

    # Now write the index
    # If root, check for dead links too
    with open(ifile_local_path, 'w') as ifile:
        ifile.write(index_head.format(this_dir=remote_path))
        for filename in remote_files:
            if update_root: # Check deadlinks
                sub_index = os.path.join(filename,IFILENAME) #Filename includes remote_path
                print(f"Looking for {sub_index}")
                try:
                    client.head_object(Bucket=bucket, Key=sub_index)
                    ifile.write(index_link.format(link=filename))
                    print(f"Found {sub_index}")
                except botocore.exceptions.ClientError:
                    print(f"Could not find {sub_index} - will not write link")
            else:
                relative_filename = os.path.relpath(filename, remote_path)
                ifile.write(index_link.format(link=relative_filename))
        ifile.write(index_tail)

    try:
        client.upload_file(ifile_local_path, Bucket=bucket, Key=ifile_remote_path,
                        ExtraArgs={'ContentType':'text/html','ACL':'public-read'})
        success = True
    except botocore.exceptions.ClientError as e:
        print(f"Encountered error in writing index to S3: {e}")
        success = False

    return success

@mock_s3
def mock_update_index_files(bucket: str, remote_path: str, data_dir: str, update_root=False) -> bool:
    """
    Mocks checking a specified remote path on the S3 bucket, 
    creating index.html where it does not exist.
    Because this is a mock, we populate the remote with a few entries first.
    This index reflects both newly-added AND extant files on the specified bucket,
    as it should be called after uploading new files
    (but may also be called on its own to rebuild index.html).
    :param bucket: str of S3 bucket
    :param remote_path: str of path to upload to
    :param data_dir: str of the data directory, where the index will temporarily be saved
    :param update_root: bool, True to update root index, which performs extra dead link checks
    :param existing_client: an existing mock S3 client object, for mock persistence 
    :return: bool returns True if all index files created successfully
    """
    
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    os.environ['AWS_SECURITY_TOKEN'] = 'test'
    os.environ['AWS_SESSION_TOKEN'] = 'test'
    
    client = boto3.client('s3')
    client.create_bucket(Bucket=bucket)

    if update_root:
        extant_files = [os.path.join(remote_path,IFILENAME),
                        os.path.join(remote_path,"tracking.yaml"),
                        os.path.join(remote_path,"test_obo/"),
                        os.path.join(remote_path,"test_obo_2/")]
    else:
        extant_files = [os.path.join(remote_path,IFILENAME),
                        os.path.join(remote_path,"a_directory/")]

    # Set up the mock root index first
    for filename in extant_files:
        client.put_object(Bucket=bucket, Key=filename)
    
    success = update_index_files(bucket, remote_path, data_dir, update_root, existing_client=client)

    return success