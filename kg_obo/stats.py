# stats.py

import csv
import os
import sys
import yaml # type: ignore
import boto3 # type: ignore
from importlib import import_module
import tarfile
import shutil
from typing import List

import kg_obo.upload

from ensmallen import Graph # type: ignore

IGNORED_FILES = ["index.html","tracking.yaml","lock",
                "json_transform.log", "tsv_transform.log"]
FORMATS = ["TSV","JSON"]
DATA_DIR = "./data/"

def retrieve_tracking(bucket, track_file_remote_path,
                        track_file_local_path: str = "./stats/tracking.yaml",
                        skip: list = [], 
                        get_only: list = [] ) -> list:
    """
    Downloads and parses the kg-obo tracking yaml.
    :param bucket: str of S3 bucket, to be specified as argument
    :param track_file_remote_path: path to the tracking file on the remote
    :param track_file_local_path: path where file should be downloaded
    :param skip: list of OBOs to skip, by ID
    :param get_only: list of OBOs to retrieve, by ID (otherwise do all)
    :return: dict of tracking file contents (OBO names, IRIs, and all versions)
    """   

    # We'll get a list of dicts so it's nicely iterable
    # Name isn't primary key as it may have multiple versions
    # So each OBO name + version is its own list entry
    versions: List[dict]  = []

    client = boto3.client('s3')

    client.download_file(Bucket=bucket, Key=track_file_remote_path, Filename=track_file_local_path)

    with open(track_file_local_path, 'r') as track_file:
        tracking = yaml.load(track_file, Loader=yaml.BaseLoader)

    # Need to flatten a bit
    for name in tracking["ontologies"]:
        if name in skip:
            continue
        if len(get_only) > 0 and name not in get_only:
            continue
        current_version = tracking["ontologies"][name]["current_version"]
        add_all_formats(versions, name, current_version)
        # See if there are archived versions
        if "archive" in tracking["ontologies"][name]:
            for entry in tracking["ontologies"][name]["archive"]:
                archive_version = entry["version"]
                add_all_formats(versions, name, archive_version)
            
    return versions

def add_all_formats(inlist, name, version) -> list:
    """
    Given a list of dicts of the form produced by retrieve_tracking,
    adds a new name and version in all extant file formats.
    :param inlist: list of dicts
    :param name: value for Name
    :param version: value for Version
    :return: list with new dict entries added
    """

    for file_format in FORMATS:
        inlist.append({"Name": name, 
                        "Version": version, 
                        "Format": file_format})

    return inlist

def write_stats(stats, outpath) -> None:
    """
    Writes OBO graph stats or validation file to tsv.
    :param stats: dict of stats in which keys are OBO names
    """
    columns = (stats[0]).keys()

    with open(outpath, 'w') as outfile:
        writer = csv.DictWriter(outfile, delimiter='\t',
                                fieldnames=columns)
        writer.writeheader()
        for entry in stats:
            writer.writerow(entry)
    
    print(f"Wrote to {outpath}")

def get_file_list(bucket, remote_path, versions) -> dict:
    """
    Given a list of dicts of OBO names and versions,
    retrieve the list of all matching keys from the remote.
    :param bucket: str of S3 bucket, to be specified as argument
    :param remote_path: str of remote directory to start from
    :param versions: list of dicts returned from retrieve_tracking
    :return: dict of OBO keys and formats
    """

    metadata = {}
    remote_files = [] # All file keys

    client = boto3.client('s3')
    pager = client.get_paginator('list_objects_v2')

    names = [entry["Name"] for entry in versions]

    try:
        for page in pager.paginate(Bucket=bucket, Prefix=remote_path+"/"):
            remote_contents = page['Contents']
            for key in remote_contents:
                if os.path.basename(key['Key']) not in IGNORED_FILES and \
                    ((key['Key']).split("/"))[1] in names:
                    remote_files.append(key['Key'])
                    metadata[key['Key']] = {"LastModified": key['LastModified'],
                                            "Size": key['Size'] }
                    if key['Key'].endswith(".tar.gz"):
                        metadata[key['Key']]["Format"] = "TSV"
                    elif key['Key'].endswith(".json"):
                        metadata[key['Key']]["Format"] = "JSON"
    except KeyError:
        print(f"Found no existing contents at {remote_path}")

    return metadata

def get_clean_file_metadata(bucket, remote_path, versions) -> dict:
    """
    Given a list of dicts of OBO names and versions,
    retrieve their metadata from the remote.
    For now this obtains the time each file was last modified.
    Retrieving the remote file list is done by a get_file_list.
    :param bucket: str of S3 bucket, to be specified as argument
    :param remote_path: str of remote directory to start from
    :param versions: list of dicts returned from retrieve_tracking
    :return: dict of dicts, with OBO names as 1ary keys, versions and file formats as 
            2ary keys, and metadata as key-value pairs
    """

    metadata = {}
    clean_metadata = {} # type: ignore

    metadata = get_file_list(bucket, remote_path, versions)

    # Metadata will be empty if files don't exist for some reason,
    # or if the specified OBO name doesn't exist.
    # Will still continue if any OBO files can be found,
    # and will simply ignore the missing ones.
    if len(metadata) == 0:
        sys.exit("Could not find OBO files on remote - please check names.")

    # Clean up the keys so they're indexable
    for entry in metadata:
        name = (entry.split("/"))[1]
        version = (entry.split("/"))[2]
        file_format = metadata[entry].pop("Format")
        if name in clean_metadata and version in clean_metadata[name]:
            clean_metadata[name][version][file_format] = metadata[entry]
        elif name in clean_metadata and version not in clean_metadata[name]:
            clean_metadata[name][version] = {file_format:metadata[entry]}
        else:
            clean_metadata[name] = {version:{file_format:metadata[entry]}}

    return clean_metadata

def decompress_graph(name, outpath) -> tuple:
    """
    Decompresses a graph file to its node and edgelists.
    Does a quick validation to ensure they aren't empty.
    Assumes there is a single tar.gz file in the provided dir.
    :param name: name to assign the prefix of the output files
    :param outpath: path to the compressed graph file
    :return: tuple of path of edgelist, path of nodelist
    """

    graph_file = tarfile.open(outpath, "r:gz")
    outdir = os.path.dirname(outpath)

    i = 0
    for tarmember in graph_file.getmembers():
        if "_kgx_tsv_" in tarmember.name:
            graph_file.extract(tarmember, outdir)
            i = i+1
        if i > 2:
            sys.exit(f"Compressed graph file contains unexpected members!")
    graph_file.close()

    edges_path = os.path.join(outdir,f"{name}_kgx_tsv_edges.tsv")
    nodes_path = os.path.join(outdir,f"{name}_kgx_tsv_nodes.tsv")

    path_pair = (edges_path, nodes_path)

    for filepath in path_pair: # Verify the files aren't empty
        with open(filepath, "r") as infile:
            lines = infile.readlines()
            if len(lines) < 2:
                print(f"{filepath} looks empty!")
                path_pair = ("EMPTY", "EMPTY")

    return path_pair

def get_graph_details(bucket, remote_path, versions) -> dict:
    """
    Given a list of dicts of OBO names and versions,
    get details about their graph structure:
    node count, edge count, component count, and
    count of singletons.
    This is version-dependent; each version has its own
    details.

    This function relies upon grape/ensmallen,
    as it works very nicely with kg-obo's graphs.

    Graph stats are:
      Nodes: node count
      Edges: edge count
      ConnectedComponents: triple of (number of components, 
        number of nodes of the smallest component, and
        number of nodes of the biggest component)
      Singletons: count of singleton nodes
      MaxNodeDegree: degree value of node with largest degree
      MeanNodeDegree: (unweighted) mean node degree for the graph

    :param bucket: str of S3 bucket, to be specified as argument
    :param remote_path: str of remote directory to start from
    :param versions: list of dicts returned from retrieve_tracking
    :return: dict of dicts, with file paths as keys, versions and 2ary keys, 
                and metadata as key-value pairs
    """

    #TODO: use the ensmallen automatic loading, for Maximum Speed

    client = boto3.client('s3')

    graph_details = {} # type: ignore

    # Get the list of file keys first so we refer back for downloads
    metadata = get_file_list(bucket, remote_path, versions)
    clean_metadata = {} # type: ignore

    # Clean up the metadata dict so we can index it
    for entry in metadata:
        name = (entry.split("/"))[1]
        version = (entry.split("/"))[2]
        if name in clean_metadata and version in clean_metadata[name]:
            clean_metadata[name][version]["path"] = entry
        elif name in clean_metadata and version not in clean_metadata[name]:
            clean_metadata[name][version] = {"path":""}
        else:
            clean_metadata[name] = {version:{"path":""}}

    for entry in clean_metadata:
        os.mkdir(os.path.join(DATA_DIR,entry))
        for version in clean_metadata[entry]:
            print(f"Downloading {entry}, version {version} from KG-OBO.")
            outdir = os.path.join(DATA_DIR,entry,version)
            outpath = os.path.join(outdir,"graph.tar.gz")
            os.mkdir(outdir)

            client.download_file(bucket, 
                                clean_metadata[entry][version]['path'],
                                outpath)

            # Decompress
            edges_path, nodes_path = decompress_graph(entry, outpath)
            if edges_path == "EMPTY" or nodes_path == "EMPTY":
                continue #Skip this one if the files are empty
            
            g = Graph.from_csv(name=f"{entry}_version_{version}",
                                edge_path=edges_path,
                                sources_column="subject",
                                destinations_column="object",
                                edge_list_header = True,
                                edge_list_separator="\t",
                                node_path = nodes_path,
                                nodes_column = "id",
                                node_list_header = True,
                                node_list_separator="\t",
                                directed =False,
                                verbose=True
                                )
            
            node_count = g.get_nodes_number()
            edge_count = g.get_edges_number()
            connected_components = g.get_connected_components_number()
            singleton_count = g.get_singleton_nodes_number()
            max_node_degree = g.get_maximum_node_degree()
            mean_node_degree = g.get_node_degrees_mean() 

            graph_stats = {"Nodes":node_count,
                            "Edges":edge_count,
                            "ConnectedComponents":connected_components,
                            "Singletons":singleton_count,
                            "MaxNodeDegree": max_node_degree,
                            "MeanNodeDegree": "{:.2f}".format(mean_node_degree)}
        
            if entry in graph_details: # i.e., we have >1 version
                graph_details[entry][version] = graph_stats
            else:
                graph_details[entry] = {version:graph_stats}

    return graph_details

def validate_version_name(version) -> bool:
    """
    Given an ontology version name, checks if it is all spaces,
    poorly formatted, or contains other issues.
    :param version: string of version name
    :return: bool, True if version is valid, False if not
    """
    valid = True

    if version in ["release","\n________"] or "%" in version:
        valid = False

    return valid

def get_all_stats(skip: list = [], get_only: list = [], bucket="bucket",
                    save_local = False):
    """
    Get graph statistics for all specified OBOs.
    :param skip: list of OBOs to skip, by ID
    :param get_only: list of OBOs to retrieve, by ID (otherwise do all)
    :param bucket: str of S3 bucket, to be specified as argument
    :param save_local: if True, retains all downloaded files. Deletes them otherwise.
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
    versions = retrieve_tracking(bucket, track_file_remote_path,
                                 "./stats/tracking.yaml",
                                 skip, get_only)
    validations = []

    # Get metadata from remote files
    print("Retrieving file metadata.")
    clean_metadata = get_clean_file_metadata(bucket, "kg-obo", versions)

    # Get graph details
    graph_details = get_graph_details(bucket, "kg-obo", versions)

    # Now merge metadata into what we have from before
    for entry in versions:
        issues = []
        try:
            name = entry["Name"]
            version = entry["Version"]
            file_format = entry["Format"] #Just a placeholder initially
            step = "metadata"
            entry.update(clean_metadata[name][version][file_format])
            step = "graph details"
            entry.update(graph_details[name][version])

            if not validate_version_name(version):
                issues.append(f"Invalid version name")

            validations.append({"Name": name, "Version": version,
                                "Format": file_format,
                                "Issue": "|".join(issues)})
        except KeyError: #Some entries still won't have metadata
            print(f"Missing {step} for {name}, version {version}.")
            issues.append(f"Missing {step}")
            validations.append({"Name": name, "Version": version,
                                "Format": file_format,
                                "Issue": "|".join(issues)})
            continue
        # Remove all local data files
        if not save_local:
            outdir = os.path.join(DATA_DIR,entry["Name"])
            if os.path.isdir(outdir):
                shutil.rmtree(outdir)

    # Time to write
    for data, outpath in [(versions, "stats/stats.tsv"),
                    (validations, "stats/validation.tsv")]:
        write_stats(data, outpath)

    return success
