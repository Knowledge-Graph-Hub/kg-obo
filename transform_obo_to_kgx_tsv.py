import logging
import tempfile

from tqdm import tqdm
import yaml
import boto3
import requests
import urllib.request
import os

# this is a stable URL containing a YAML file that describes all the OBO ontologies:
# get the ID for each ontology, construct PURL
import yaml
from botocore.exceptions import ClientError

source_of_obo_truth = 'https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml'
with urllib.request.urlopen(source_of_obo_truth) as f:
    yaml_content = f.read().decode('utf-8')
    yaml_parsed = yaml.safe_load(yaml_content)


def upload_dir_to_s3(local_directory: str, s3_bucket: str, s3_bucket_dir: str,
                     make_public=False) -> None:
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
            except ClientError:  # Exception abuse
                ExtraArgs = None
                if make_public:
                    ExtraArgs = {'ACL': 'public-read'}

                logging.info(f"Uploading {s3_path}")
                client.upload_file(local_path, s3_bucket, s3_path, ExtraArgs=ExtraArgs)


def base_url_if_exists(oid):
    ourl = f"http://purl.obolibrary.org/obo/{oid}/{oid}-base.owl"
    try:
        ret = requests.head(ourl, allow_redirects=True)
        if ret.status_code != 200:
            ourl = f"http://purl.obolibrary.org/obo/{oid}.owl"
        else:
            i = 0
            for line in urllib.request.urlopen(ourl):
                i = i + 1
                if i > 3:
                    break
                l = line.decode('utf-8')
                if "ListBucketResult" in l:
                    ourl = f"http://purl.obolibrary.org/obo/{oid}.owl"

    except Exception:
        ourl = f"http://purl.obolibrary.org/obo/{oid}.owl"
    return ourl


for o in tqdm(yaml_parsed['ontologies'], "processing ontologies"):
    url = base_url_if_exists(o['id'])  # take base if it exists, otherwise just use non-base
    # TODO: generate base if it doesn't exist, using robot

    tf = tempfile.NamedTemporaryFile()
    outfile = "outfile.owl"

    # download url
    urllib.request.urlretrieve(url, tf.name)

    # use kgx to convert OWL to KGX tsv

    # upload to S3
