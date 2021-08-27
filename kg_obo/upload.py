import botocore.exceptions  # type: ignore
import boto3  # type: ignore
import os
import logging

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
                extra_args = None
                if make_public:
                    extra_args = {'ACL': 'public-read'}

                logging.info(f"Uploading {s3_path}")
                client.upload_file(local_path, s3_bucket, s3_path, ExtraArgs=extra_args)

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
