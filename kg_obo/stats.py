# stats.py

import csv
import os
import yaml # type: ignore
import boto3 # type: ignore

import kg_obo.upload

def retrieve_tracking(bucket, track_file_remote_path, skip: list = [], 
                        get_only: list = [] ) -> list:
    """
    Downloads and parses the kg-obo tracking yaml.
    :param bucket: str of S3 bucket, to be specified as argument
    :param tracking_file_remote_path: path to the tracking file on the remote
    :return: dict of tracking file contents (OBO names, IRIs, and all versions)
    """   

    # We'll get a list of dicts so it's nicely iterable
    # Name isn't primary key as it may have multiple versions
    # So each OBO name + version is its own list entry
    versions = [] 

    track_file_local_path = "stats/tracking.yaml"

    client = boto3.client('s3')

    client.download_file(Bucket=bucket, Key=track_file_remote_path, Filename=track_file_local_path)

    with open(track_file_local_path, 'r') as track_file:
        tracking = yaml.load(track_file, Loader=yaml.BaseLoader)

    print(tracking)

    # Need to flatten a bit
    for name in tracking["ontologies"]:
        if name in skip:
            continue
        if len(get_only) > 0 and name not in get_only:
            continue
        current_version = tracking["ontologies"][name]["current_version"]
        versions.append({"Name": name, "Version": current_version})
        # See if there are archived versions
        if "archive" in tracking["ontologies"][name]:
            for entry in tracking["ontologies"][name]["archive"]:
                archive_version = entry["version"]
                versions.append({"Name": name, "Version": archive_version})
            
    return versions

def write_stats(stats) -> None:
    """
    Writes OBO graph stats to tsv.
    :param stats: dict of stats in which keys are OBO names
    """

    outpath = "stats/stats.tsv"
    columns = ["Name","Version"]

    with open(outpath, 'w') as outfile:
        writer = csv.DictWriter(outfile, delimiter='\t',
                                fieldnames=columns)
        writer.writeheader()
        for entry in stats:
            writer.writerow(entry)

def get_graph_stats(skip: list = [], get_only: list = [], bucket="bucket"):
    """
    Get graph statistics for all specified OBOs.
    :param skip: list of OBOs to skip, by ID
    :param get_only: list of OBOs to retrieve, by ID (otherwise do all)
    :param bucket: str of S3 bucket, to be specified as argument
    :return: boolean indicating success or existing run encountered (False for unresolved error)
    """
    success = True

    track_file_remote_path = "kg-obo/tracking.yaml"

    if len(skip) >0:
      print(f"Ignoring these OBOs: {skip}" )
    if len(get_only) >0:
       print(f"Will only retrieve these OBOs: {get_only}" ) 

    # Set up local directories
    if not os.path.exists("./stats/"):
        os.mkdir("stats")

    # Check for the tracking file first
    if not kg_obo.upload.check_tracking(bucket, track_file_remote_path):
        print("Cannot locate tracking file on remote storage. Exiting...")
        return False

    # Get current versions for all OBO graphs
    # Or just the specified ones
    versions = retrieve_tracking(bucket, track_file_remote_path, skip, get_only)

    # Time to write
    write_stats(versions)

    return success
