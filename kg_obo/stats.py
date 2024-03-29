# stats.py

import csv
import os
import shutil
import sys
import tarfile
from typing import Dict, List

import boto3  # type: ignore
import botocore.exceptions  # type: ignore
import yaml  # type: ignore
from grape import Graph  # type: ignore

import kg_obo.upload
from kg_obo.robot_utils import initialize_robot, measure_owl

IGNORED_FILES = ["index.html",
                 "json_transform.log",
                 "kg-obo_version",
                 "lock",
                 "tracking.yaml",
                 "tsv_transform.log",
                 "unexpected_ids.tsv",
                 "update_id_maps.tsv"]
FORMATS = ["TSV","JSON"]
DATA_DIR = "./data/"

SIZE_DIFF_TYPES = ["Large Difference in Size",
                    "Large Difference in Node Count",
                    "Large Difference in Edge Count"]

def retrieve_tracking(bucket, track_file_remote_path,
                        track_file_local_path: str = "./tracking.yaml",
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
    :param outpath: string for path to write file to
    """

    try:
        columns = list((stats[0]).keys())
    except IndexError: # Raised if input is empty
        columns = []
    
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
    For now we ignore owl and version files.
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
    Here, we ignore additional non-transform contents of each directory.
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
        filetype = (entry.split("."))[-1]
        if filetype in ['json','gz']:
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
            cleanup(name)
            sys.exit("Compressed graph file contains unexpected members!")
    graph_file.close()

    edges_path = os.path.join(outdir,f"{name}_kgx_tsv_edges.tsv")
    nodes_path = os.path.join(outdir,f"{name}_kgx_tsv_nodes.tsv")

    path_pair = (edges_path, nodes_path) # type: ignore

    for filepath in path_pair: # Verify the files aren't empty
        with open(filepath, "r") as infile:
            lines = infile.readlines()
            if len(lines) < 2:
                print(f"{filepath} looks empty!")
                path_pair = None # type: ignore

    return path_pair

def get_graph_details(bucket, remote_path, versions) -> dict:
    """
    Given a list of dicts of OBO names and versions,
    get details about their graph structure:
    node count, edge count, component count, and
    count of singletons.
    This is version-dependent; each version has its own
    details.
    Ignores anything that isn't a tar.gz or a json file.

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
    :return: dict of dicts, with file paths as keys, versions are 2ary keys, 
                and metadata as key-value pairs
    """

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
        try:
            os.mkdir(os.path.join(DATA_DIR,entry))
        except FileExistsError: #If folder exists, don't need to make it.
            pass

        # We download the compressed graph nodes/edges
        # then load with ensmallen and get graph details
        for version in clean_metadata[entry]:
            remote_loc = clean_metadata[entry][version]['path']
            print(f"Downloading {entry}, version {version} from KG-OBO: {remote_loc}")
            outdir = os.path.join(DATA_DIR,entry,version)
            outpath = os.path.join(outdir,"graph.tar.gz")
            try:
                os.mkdir(outdir)
            except FileExistsError: #If folder exists, don't need to make it.
                pass

            if not os.path.exists(outpath):
                client.download_file(bucket, 
                                remote_loc,
                                outpath)
            else:
                print(f"Found existing graph file for {entry} at {outpath}. Will use.")

            # Decompress
            path_pair = decompress_graph(entry, outpath)
            if not path_pair:
                continue #Skip this one if the files are empty
            else:
                edges_path, nodes_path = path_pair
                
            g = load_graph(entry, version, edges_path, nodes_path)
            
            node_count = g.get_number_of_nodes()
            edge_count = g.get_number_of_edges()
            connected_components = g.get_number_of_connected_components()
            singleton_count = g.get_number_of_singleton_nodes()
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

def load_graph(name: str, version: str, edges_path: str, 
                nodes_path: str) -> Graph:
    """
    Load a graph with Ensmallen (from grape).
    :param name: OBO name
    :param version: OBO version
    :param edges_path: path to edgefile
    :param nodes_path: path to nodefile
    :return: ensmallen Graph object
    """

    loaded_graph = Graph.from_csv(name=f"{name}_version_{version}",
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

    return loaded_graph


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

def compare_versions(entry, versions) -> dict:
    """
    Given an entry from the full set of versions,
    compare it to other versions of the same OBO name.
    Identify versions with >50% increase/decrease in file size,
    or versions with >20% increase/decrease in node or edge count.
    :param entry: dict of single OBO entry
    :param versions: dict of all versions, with added graph details
    :return: dict of versions with notes as described above.
    """

    compare: Dict[str, list] = {SIZE_DIFF_TYPES[0]:[],
                                SIZE_DIFF_TYPES[1]:[],
                                SIZE_DIFF_TYPES[2]:[]}

    # Duplicate the versions and remove target entry

    new_versions = versions.copy()
    try:
        for i in range(len(new_versions)):
            if new_versions[i]['Name'] == entry['Name'] and \
                new_versions[i]['Version'] == entry['Version'] and \
                new_versions[i]['LastModified'] == entry['LastModified']:
                del new_versions[i]
                break
    
        for other_entry in new_versions:
            # Check other versions to see if they're v. different in size
            if other_entry['Name'] == entry['Name'] and \
                other_entry['Format'] == entry['Format'] and \
                    other_entry['Version'] != entry['Version']:
                
                # Check raw file size difference
                size_diff = abs(entry['Size'] / other_entry['Size'])
                if not 0.5 <= size_diff <= 1.5:
                    compare[SIZE_DIFF_TYPES[0]].append(other_entry['Version'])

                # Check node count difference
                size_diff = abs(entry['Nodes'] / other_entry['Nodes'])
                if not 0.2 <= size_diff <= 1.2:
                    compare[SIZE_DIFF_TYPES[1]].append(other_entry['Version'])

                # Check edge count difference
                size_diff = abs(entry['Edges'] / other_entry['Edges'])
                if not 0.2 <= size_diff <= 1.2:
                    compare[SIZE_DIFF_TYPES[2]].append(other_entry['Version'])

    except KeyError:
        pass

    return compare

def cleanup(dir: str) -> None:
    """
    Removes files for a given OBO from the data directory.
    :param dir: str for name of the directory
    """

    outdir = os.path.join(DATA_DIR,dir)
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)


def robot_axiom_validations(bucket: str, remote_path: str,
                            robot_path: str, robot_env: dict, 
                            versions: list) -> list:
    """
    Runs three steps for each OBO:
    1. Gets metrics on each original OWL and writes to file
    2. Loads list of axiom counts by namespace
    3. Locates edges involving each namespace in the graph.
    Produces a log file for each set of metrics.

    This assumes that get_graph_details has already been run,
    as that's when all the graph downloads happen,
    and we don't need to do those multiple times.
    But we still need original OWLs, which we retrieve from KG-HUB.

    :param bucket: str of S3 bucket, to be specified as argument
    :param remote_path: str of remote directory to start from
    :param robot_path: str of path to robot, usually in pwd
    :param robot_env: dict of robot environment variables
    :param versions: list of dicts of each OBO name and version and format
    :return: dict of dicts, with OBO names as 1ary keys, versions as 
            2ary keys, and metadata as key-value pairs
    """

    client = boto3.client('s3')

    wanted_metrics = ['namespace_axiom_count']

    validations_vs_owl = []

    for entry in versions:
        if entry["Format"] == 'TSV': # Just the TSVs for now
            # Retreive OWL for each.
            # Skip if it isn't available for any reason.

            name = entry["Name"]
            version = entry["Version"]
            remote_loc = f'kg-obo/{name}/{version}/{name}.owl'
            print(f"Downloading OWL for {name}, version {version} from KG-OBO: {remote_loc}")
            outdir = os.path.join(DATA_DIR,name,version)
            outpath = os.path.join(outdir,f"{name}.owl")
            logdir = os.path.join("stats",name,version)
            logpath = os.path.join(logdir,f"{name}-owl-profile-validation.tsv")
            try:
                os.makedirs(logdir)
            except FileExistsError: #If folder exists, don't need to make it.
                pass

            try:
                # Check if it exists first
                client.head_object(Bucket=bucket, Key=remote_loc)
                client.download_file(bucket, remote_loc, outpath)
            except botocore.exceptions.ClientError as e:
                print(f"Could not retrieve OWL for {name}, version {version} due to: {e}")
                shutil.rmtree(logdir)
                continue

            # Check to see if we already have robot measure results
            # to avoid a redundant operation.
            # If we have 'em, download 'em
            try:
                remote_metrics = f'kg-obo/{name}/{version}/{name}-owl-profile-validation.tsv'
                client.head_object(Bucket=bucket, Key=remote_metrics)
                print(f"Will download existing metrics for {name}, version {version}.")
                client.download_file(bucket, remote_metrics, logpath)
                need_metrics = False
            except botocore.exceptions.ClientError:
                need_metrics = True
                print(f"Will get metrics for {name}, version {version}.")

            # Run robot measure to get stats we'll use for comparison
            # and load its output
            if need_metrics:
                if measure_owl(robot_path, outpath, logpath, robot_env):
                    print(f"Generated new ROBOT metrics for {name}, version {version}.")
                    pass
                else:
                    print(f"Failed to obtain metrics for {name}, version {version}.")
                    continue
            try:
                metrics = parse_robot_metrics(logpath, wanted_metrics)
            except FileNotFoundError: # If we still don't have metrics
                print(f"No metrics could be obtained for {name}, version {version}.")
                continue
            
            # Load the graph
            edges_path = os.path.join(outdir,f"{name}_kgx_tsv_edges.tsv")
            nodes_path = os.path.join(outdir,f"{name}_kgx_tsv_nodes.tsv")
            g = load_graph(entry, version, edges_path, nodes_path)

            # Get axiom namespaces
            owl_namespaces = []
            missing_namespaces = []
            try: # Sometimes we need to use namespace_axiom_count_incl
                for namespace_and_count in metrics['namespace_axiom_count']:
                    namespace = (namespace_and_count.split())[0]
                    owl_namespaces.append(namespace)
            except KeyError:
                for namespace_and_count in metrics['namespace_axiom_count_incl']:
                    namespace = (namespace_and_count.split())[0]
                    owl_namespaces.append(namespace)
                
            # Compare axiom namespaces in OWL and in graph 
            # We don't expect a perfect numerical match,
            # but we do want to know which types of axioms are present (or not)
            graph_namespaces = []
            for item in g.get_node_names():
                graph_namespaces.append((item.split(":"))[0])
            graph_namespaces = list(set(graph_namespaces))
            for namespace in owl_namespaces:
                if namespace not in graph_namespaces:
                    missing_namespaces.append(namespace)

            # Append what we got
            these_validations = {"Name":name,
                                "Version":version,
                                "Format":entry["Format"],
                                "OWL Namespaces":"|".join(owl_namespaces),
                                "Graph Namespaces":"|".join(graph_namespaces),
                                "OWL Namespaces Not In Graph":"|".join(missing_namespaces)}
            validations_vs_owl.append(these_validations)
    
    return validations_vs_owl

def parse_robot_metrics(inpath: str, wanted_metrics: list) -> dict:
    '''
    Opens a tsv file containing results of a robot measure command.
    Returns contents as a dict of lists with metric names as keys
    and metric values as values, given a list of desired metrics.
    If wanted_metrics is empty then all metrics are parsed.
    :param inpath: str of path to tsv file to load
    :param wanted_metrics: list of metrics to get, e.g. ['axiom_types', 'class_count']
    :return: dict of specific metrics and values as list 
    '''

    metrics = {}

    owl_metrics = csv.DictReader(open(inpath, 'r'), delimiter='\t')
    for line in owl_metrics:
        if line['metric'] not in metrics:
            metrics[line['metric']] = [line['metric_value']]
        else:
            metrics[line['metric']].append(line['metric_value'])

    if len(wanted_metrics) > 0:
        try:
            new_metrics = {k: metrics[k] for k in wanted_metrics}
            metrics = new_metrics
        except KeyError:
            pass # Can't update if the wanted metric doesn't exist
        
    return metrics 


def get_all_stats(skip: list = [], 
                    get_only: list = [], 
                    bucket="bucket",
                    save_local = False,
                    no_robot = False):
    """
    Get graph statistics for all specified OBOs.
    :param skip: list of OBOs to skip, by ID
    :param get_only: list of OBOs to retrieve, by ID (otherwise do all)
    :param bucket: str of S3 bucket, to be specified as argument
    :param save_local: if True, retains all downloaded files. Deletes them otherwise.
    :param no_robot: if True, skips all ROBOT error checking and validation.
    :return: boolean indicating success or existing run encountered (False for unresolved error)
    """
    success = True

    track_file_remote_path = "kg-obo/tracking.yaml"

    if not no_robot:
        print("Setting up ROBOT...")
        robot_path = os.path.join(os.getcwd(),"robot")
        robot_params = initialize_robot(robot_path)
        print(f"ROBOT path: {robot_path}")
        robot_env = robot_params[1]
        print(f"ROBOT evironment variables: {robot_env['ROBOT_JAVA_ARGS']}")

        if not robot_params[0]: #i.e., if we couldn't find ROBOT 
            sys.exit("\t*** Could not locate ROBOT - ensure it is available and executable. \n\tExiting...")

    # Make local stats directory
    try:
        os.mkdir("stats")
    except FileExistsError: #If folder exists, don't need to make it.
        pass

    # Check for the tracking file first
    if not kg_obo.upload.check_tracking(bucket, track_file_remote_path):
        print("Cannot locate tracking file on remote storage. Exiting...")
        return False

    # Get current versions for all OBO graphs
    # Or just the specified ones
    versions = retrieve_tracking(bucket, track_file_remote_path,
                                 "./tracking.yaml",
                                 skip, get_only)
    validations = []

    # Get metadata from remote files
    print("Retrieving file metadata.")
    clean_metadata = get_clean_file_metadata(bucket, "kg-obo", versions)

    # Get graph details
    graph_details = get_graph_details(bucket, "kg-obo", versions)

    # Need to do comparison-based validations
    # after all data population

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

            step = "validation"
            if not validate_version_name(version):
                issues.append("Invalid version name")

            if entry["Edges"] == 1:
                issues.append("Single edge")

        except KeyError: #Some entries still won't have metadata
            print(f"Missing {step} for {name}, version {version}.")
            issues.append(f"Missing {step}")
            validations.append({"Name": name, "Version": version,
                                "Format": file_format,
                                "Issue": "|".join(issues)})
            continue

        validations.append({"Name": name, "Version": version,
                                "Format": file_format,
                                "Issue": "|".join(issues)})

    # Now validate vs. the original OWL
    if not no_robot:
        axiom_validations = robot_axiom_validations(bucket, "kg-obo", 
                                        robot_path, robot_env, versions)

    # Comparative validation time
    new_validations = []
    for entry in versions:
        issues = []
        compare = compare_versions(entry, versions)
        very_different_versions = [compare[SIZE_DIFF_TYPES[0]],
                                    compare[SIZE_DIFF_TYPES[1]],
                                    compare[SIZE_DIFF_TYPES[2]]]
        i = 0
        for count in very_different_versions:                     
            if len(count) > 0:
                issues.append(f"{SIZE_DIFF_TYPES[i]}: {count}")
                break
            i = i +1
        
        # TODO: Should probably refactor this
        for val_entry in validations:
            if entry["Name"] == val_entry["Name"] \
                and entry["Version"] == val_entry["Version"] \
                and entry["Format"] == val_entry["Format"]:
                issues = issues + (val_entry["Issue"]).split("|")
        issues = [i for i in issues if i] # No empty entries
        new_validations_entry = {"Name": entry["Name"], 
                                "Version": entry["Version"],
                                "Format": entry["Format"],
                                "Issue": "|".join(issues)}
        new_validations.append(new_validations_entry)

        # Clean up local data files
        if not save_local:
            cleanup(entry["Name"])

    # Clean up the output before writing
    final_versions = []
    final_versions = [i for n, i in enumerate(versions) if i not in versions[n + 1:]]
    final_validations = []
    final_validations = [i for n, i in enumerate(new_validations) if i not in new_validations[n + 1:]]

    # Time to write
    stats_paths = ["stats/stats.tsv", "stats/validation.tsv", "stats/axiom_validations.tsv"]
    write_stats(final_versions, stats_paths[0])
    print(f"Wrote stats on all ontologies and versions to {stats_paths[0]}")
    write_stats(final_validations, stats_paths[1])
    print(f"Wrote validations for all ontologies and versions to {stats_paths[1]}")
    if not no_robot:
        write_stats(axiom_validations, stats_paths[2])
        print(f"Wrote axiom analyses for all ontologies and versions to {stats_paths[2]}")

    return success
