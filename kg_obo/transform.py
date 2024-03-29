import difflib
import hashlib
import logging
import mmap
import os
import re
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime
from io import StringIO
from xml.sax._exceptions import SAXParseException  # type: ignore

import boto3  # type: ignore
import git
import kgx.cli  # type: ignore
import requests  # type: ignore
import yaml  # type: ignore
from curies import Converter  # type: ignore
from kgx.config import get_logger  # type: ignore
from prefixmaps.io.parser import load_multi_context  # type: ignore
from rdflib.exceptions import ParserError  # type: ignore
from tqdm import tqdm  # type: ignore

import kg_obo.obolibrary_utils
import kg_obo.upload
from kg_obo.prefixes import KGOBO_PREFIXES
from kg_obo.robot_utils import (
    convert_owl,
    examine_owl_names,
    initialize_robot,
    merge_and_convert_owl,
    relax_owl,
)


KGOBO_TRACK_FILE = "kg-obo/tracking.yaml"

def delete_path(root_dir: str, omit: list = []) -> bool:
    """Deletes a path recursively, i.e., everything in
    the provided directory and all its subdirectories.
    :param root_dir: str of the path to begin with
    :param omit: list of path(s) to keep, i.e., don't delete them
    :return: bool, True if successful
    """
    success = True

    try:
        for filename in os.listdir(root_dir):
            file_path = os.path.join(root_dir, filename)
            if filename not in omit:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
    except IOError as e:
        print(f"Error in deleting {root_dir}: {e}")
        success = False

    return success


def retrieve_obofoundry_yaml(
    yaml_url: str = "https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml",
    skip: list = [],
    get_only: list = [],
) -> list:
    """Retrieve YAML containing list of all ontologies in OBOFoundry
    :param yaml_url: a stable URL containing a YAML file that describes all the OBO ontologies:
    :param skip: which ontologies should we skip
    :return: parsed yaml describing ontologies to transform
    """
    yaml_req = requests.get(yaml_url)
    yaml_content = yaml_req.content.decode("utf-8")
    yaml_parsed = yaml.safe_load(yaml_content)
    yaml_onto_list: list = yaml_parsed["ontologies"]

    if len(skip) > 0:
        yaml_onto_list_filtered = [
            ontology
            for ontology in yaml_onto_list
            if ontology["id"] not in skip
            if ("is_obsolete" not in ontology) or not (ontology["is_obsolete"])
        ]
    elif len(get_only) > 0:
        yaml_onto_list_filtered = [
            ontology
            for ontology in yaml_onto_list
            if ontology["id"] in get_only
            if ("is_obsolete" not in ontology) or not (ontology["is_obsolete"])
        ]
    else:
        yaml_onto_list_filtered = [
            ontology
            for ontology in yaml_onto_list
            if ("is_obsolete" not in ontology) or not (ontology["is_obsolete"])
        ]

    return yaml_onto_list_filtered


def kgx_transform(
    input_file: list,
    input_format: str,
    output_file: str,
    output_format: str,
    logger: object,
    knowledge_sources: list,
) -> tuple:
    """Call KGX transform and report success status (bool)

    :param input_file: list of files to transform
    :param input_format: input format
    :param output_file: output file root
    :param output_format: output format
    :param logger: logger
    :param knowledge_sources: list of tuples for knowledge sources
    :return: tuple - (bool for did transform work?,
    bool for any errors encountered, str for error msg)
    """
    success = True
    errors = False

    bnode_errors = "BNode Errors"
    other_errors = "Other Errors"
    output_msg = f"No errors in parsing {input_file}."

    log_file_name = f"{output_format}_transform.log"
    log_file_path = os.path.join(os.path.dirname(output_file), log_file_name)

    # We stream the KGX logs to their own output to capture them
    # and also set up log output to a file which will accompany the transformed output
    log_stream = StringIO()
    log_handler = logging.StreamHandler(log_stream)
    log_file_handler = logging.FileHandler(log_file_path)
    log_handler.setLevel(logging.WARNING)
    log_file_handler.setLevel(logging.INFO)
    # Logger doesn't know it's already an instance, so it throws an error
    try:
        logger.addHandler(hdlr=log_handler)  # type: ignore
    except TypeError:
        pass
    try:
        logger.addHandler(hdlr=log_file_handler)  # type: ignore
    except TypeError:
        pass

    try:
        kgx.cli.transform(
            inputs=input_file,
            input_format=input_format,
            output=output_file,
            output_format=output_format,
            output_compression="tar.gz",
            knowledge_sources=knowledge_sources,
        )

        # Need to parse the log output to aggregate it
        error_collect = {other_errors: 0}

        for _ in log_stream.getvalue().splitlines():
            error_collect[other_errors] = error_collect[other_errors] + 1

        if sum(error_collect.values()) > 0:  # type: ignore
            output_msg = f"Encountered errors in transforming or parsing to {output_format}: {error_collect}"
            errors = True

    except (SAXParseException, ParserError, Exception) as e:
        success = False
        output_msg = (
            f"KGX problem while transforming {input_file} to {output_format} due to {e}"
        )
        print(output_msg)

    log_handler.flush()
    log_file_handler.flush()

    return (success, errors, output_msg)


def replace_illegal_chars(input_string: str, replace_char: str) -> str:
    """
    Given a string, replaces characters likely to cause problems in S3
    bucket key names with a replacement character.
    :param input_string: string to perform replacement on
    :param replace_char: string to replace characters with
    :return: string with replaced characters
    """
    # Illegal characters should not be in links or filenames
    illegal_characters = [
        "&",
        "$",
        "@",
        "=",
        ";",
        ":",
        "+",
        ",",
        "?",
        "{",
        "}",
        "%",
        "`",
        "[",
        "]",
        "~",
        "<",
        ">",
        "#",
        "|",
        "(",
        ")",
        " ",
    ]

    for character in illegal_characters:
        input_string = input_string.replace(character, replace_char)

    return input_string


def get_owl_iri(input_file_name: str) -> tuple:
    """
    Extracts version IRI from OWL definitions.
    Here, the IRI is the full URL of the origin OWL,
    as naming conventions vary.
    Avoids much file parsing as the IRI should be near the top of the file.
    Does some string parsing to get a shorter version number.
    Versions may take multiple formats across OBOs.
    If an IRI is not provided (i.e., the OWL does not contain owl:versionIRI
    in its header metadata) then we try the value of oboInOwl:date instead.
    The date value, if present, is used as a replacement version identifier,
    not a replacement IRI.
    The rdf:about value is also checked - this may not contain a version,
    but it may contain a URL we can use as an IRI.
    :param input_file_name: name of OWL format file to extract IRI from
    :return: tuple of (str of IRI, str of version, str describing version format)
    """

    # Most IRIs take this format - there are some exceptions
    iri_tag = b'owl:versionIRI rdf:resource="(.*)"'
    iri_about_tag = b'owl:Ontology rdf:about="(.*)"'
    date_tag = (
        b'oboInOwl:date rdf:datatype="http://www.w3.org/2001/XMLSchema#string">([^<]+)'
    )
    date_dc_tag = b'dc:date xml:lang="en">([^<]+)'
    version_info_tag = b'owl:versionInfo rdf:datatype="http://www.w3.org/2001/XMLSchema#string">([^<]+)'
    short_version_info_tag = b"owl:versionInfo>([^<]+)"
    version_iri_only_tag = b'versionIRI rdf:resource="(.*)"'
    # The default IRI/version - only used if values aren't provided.
    iri = "no_iri"
    version = "no_version"

    # Keep track of where we actually find a usable version value, if any
    version_format = "none"

    try:
        with open(input_file_name, "rb", 0) as owl_file, mmap.mmap(
            owl_file.fileno(), 0, access=mmap.ACCESS_READ
        ) as owl_string:
            iri_search = re.search(iri_tag, owl_string)  # type: ignore
            iri_about_tag_search = re.search(iri_about_tag, owl_string)  # type: ignore
            version_iri_only_search = re.search(
                version_iri_only_tag, owl_string
            )  # type: ignore
            # mypy doesn't like re and mmap objects
            if iri_search:
                version_format = "versionIRI"
                iri = (iri_search.group(1)).decode("utf-8")
                try:  # We handle some edge cases here
                    version = (iri.split("/"))[-2]
                    if version == "fao":
                        version = (iri.split("/"))[-3]
                    if version == "swo.owl":
                        version = (iri.split("/"))[-1]
                except IndexError:
                    pass
            elif iri_about_tag_search:  # In this case, we likely don't have a version
                version_format = "versionInfo"
                iri = (iri_about_tag_search.group(1)).decode("utf-8")
                if (iri.split("/"))[-1] in [
                    "oae.owl",
                    "opmi.owl",
                    "ons.owl",
                    "geo.owl",
                    "dideo.owl",
                    "ino.owl",
                ]:
                    version_tag = b'owl:versionInfo xml:lang="en">([^<]+)'
                    version_search = re.search(version_tag, owl_string)  # type: ignore
                    version = (version_search.group(1)).decode("utf-8")  # type: ignore
                elif (iri.split("/"))[-1] in ["cheminf.owl"]:
                    version_tag = b'owl:versionInfo rdf:datatype="&xsd;string">([^<]+)'
                    version_search = re.search(version_tag, owl_string)  # type: ignore
                    version = (version_search.group(1)).decode("utf-8")  # type: ignore
            elif version_iri_only_search:
                version_format = "versionIRI (but missing the owl: prefix)"
                iri = (version_iri_only_search.group(1)).decode("utf-8")
                try:  # We handle some edge cases here
                    version = (iri.split("/"))[-2]
                except IndexError:
                    pass
            else:
                print("Version IRI not found.")

            # If we didn't get a version out of the IRI, look elsewhere
            if version == "no_version":

                if (iri.split("/"))[-1] in ["ICEO", "KISAO#"]:
                    version_info_tag = b'owl:versionInfo rdf:datatype="http://www.w3.org/2001/XMLSchema#decimal">([^<]+)'

                date_search = re.search(date_tag, owl_string)  # type: ignore
                date_dc_search = re.search(date_dc_tag, owl_string)  # type: ignore
                version_info_search = re.search(
                    version_info_tag, owl_string
                )  # type: ignore
                short_version_info_search = re.search(
                    short_version_info_tag, owl_string
                )  # type: ignore

                for search_type in [
                    date_search,
                    date_dc_search,
                    version_info_search,
                    short_version_info_search,
                ]:
                    if search_type and version == "no_version":
                        version_format = "a date or version info field"
                        version = (search_type.group(1)).decode("utf-8")
                if version == "no_version":
                    print("Neither versioned IRI or release date found.")

                if (
                    len(version) > 100
                ):  # Some versions are just free text, so instead of parsing we hash
                    version = (hashlib.sha256(version.encode())).hexdigest()

            version = replace_illegal_chars(version, "-")

    except ValueError:  # Should not happen unless OWL definitions are missing/broken
        print(
            "Could not parse OWL definitions enough to locate version IRI or release date."
        )

    return (iri, version, version_format)


def track_obo_version(
    name: str = "",
    iri: str = "",
    version: str = "",
    bucket: str = "",
    track_file_local_path: str = "data/tracking.yaml",
    track_file_remote_path: str = KGOBO_TRACK_FILE,
) -> None:
    """
    Writes OBO version as per IRI to tracking.yaml.
    Note this tracking file is on the root of the S3 kg-obo directory.
    :param name: name of OBO, as OBO ID, e.g. 'bfo'
    :param iri: full OBO VersionIRI, usually URL
    :param version: OBO version, usually a date
    :param track_file_local_path: where to look for local tracking.yaml file
    :param track_file_remote_path: where to look for remote tracking.yaml file
    """

    client = boto3.client("s3")

    client.download_file(
        Bucket=bucket, Key=track_file_remote_path, Filename=track_file_local_path
    )

    with open(track_file_local_path, "r") as track_file:
        tracking = yaml.load(track_file, Loader=yaml.BaseLoader)

    # Check if this OBO name is in the tracking - it usually is,
    # but it may be a new OBO, so set that up
    if name not in tracking["ontologies"]:
        tracking["ontologies"][name] = {"current_iri": "NA", "current_version": "NA"}

    # If we already have a version, move it to archive
    # If it's NA then we have no previous version
    if tracking["ontologies"][name]["current_version"] != "NA":
        # If there isn't an archive field we need to create it
        if "archive" not in tracking["ontologies"][name]:
            tracking["ontologies"][name]["archive"] = []
        prev_iri = tracking["ontologies"][name]["current_iri"]
        prev_version = tracking["ontologies"][name]["current_version"]
        tracking["ontologies"][name]["archive"].append(
            {"iri": prev_iri, "version": prev_version}
        )

    # Now set the current IRI and version to the most recent transform
    tracking["ontologies"][name]["current_iri"] = iri
    tracking["ontologies"][name]["current_version"] = version

    all_versions = tracking["ontologies"][name]
    print(f"Current versions for {name}: {all_versions}")

    with open(track_file_local_path, "w") as track_file:
        track_file.write(yaml.dump(tracking))

    client.upload_file(
        Filename=track_file_local_path,
        Bucket=bucket,
        Key=track_file_remote_path,
        ExtraArgs={"ACL": "public-read"},
    )


def transformed_obo_exists(
    name: str,
    iri: str,
    s3_test=False,
    bucket: str = "",
    tracking_file_local_path: str = "data/tracking.yaml",
    tracking_file_remote_path: str = KGOBO_TRACK_FILE,
) -> bool:
    """
    Read tracking.yaml to determine if transformed version of this OBO exists.

    :param name: string of short OBO name, e.g., bfo
    :param iri: iri of OBO version
    :return: boolean, True if this OBO and version already exist as transformed
    """

    exists = False  # Assume we don't have the OBO yet unless proven otherwise

    # If testing, assume OBO transform exists as we aren't really reading tracking
    if s3_test:
        return exists

    client = boto3.client("s3")

    client.download_file(bucket, tracking_file_remote_path, tracking_file_local_path)

    with open(tracking_file_local_path, "r") as track_file:
        tracking = yaml.load(track_file, Loader=yaml.BaseLoader)

    # Check current and previous versions
    # If it's a new OBO, we'll have a KeyError so catch that
    try:
        if tracking["ontologies"][name]["current_iri"] == iri:
            exists = True
        elif "archive" in tracking["ontologies"][name] and iri in [
            pair["iri"] for pair in tracking["ontologies"][name]["archive"]
        ]:
            exists = True
    except KeyError:
        print(f"No previous versions found for {name}!")

    return exists


def download_ontology(
    url: str, file: str, logger: object, no_dl_progress: bool, header_only: bool
) -> bool:
    """
    Download ontology from URL

    :param url: url to download from
    :param file: file to download into
    :param logger:
    :param no_dl_progress: bool, if True then download progress bar is suppressed
    :param header_only: bool, if True then only download enough of file to check IRI/version
    :return: boolean indicating whether download worked
    """
    try:
        req = requests.get(url, stream=True)
        file_size = int(req.headers["Content-Length"])
        chunk_size = 4096
        with open(file, "wb") as outfile:
            if not no_dl_progress:
                if not header_only:
                    pbar = tqdm(
                        unit="B",
                        total=file_size,
                        unit_scale=True,
                        unit_divisor=chunk_size,
                    )
                else:
                    pbar = tqdm(
                        unit="B",
                        total=chunk_size,
                        unit_scale=True,
                        unit_divisor=chunk_size,
                    )
            for chunk in req.iter_content(chunk_size=chunk_size):
                if chunk:
                    if not no_dl_progress:
                        pbar.update(len(chunk))
                    outfile.write(chunk)
                if header_only:
                    break
        return True
    except (KeyError, requests.exceptions.RequestException) as e:
        logger.error(e)  # type: ignore
        return False


def imports_requested(input_file_name: str) -> list:
    """
    Given an OWL file, searches for and returns list of import statements.
    :param file: file to parse
    :return: list of strings, each the name of an import, e.g. "upheno/metazoa.owl"
    """

    imports = []
    import_tag = b'owl:imports rdf:resource="(.*)"'

    try:
        with open(input_file_name, "rb", 0) as owl_file, mmap.mmap(
            owl_file.fileno(), 0, access=mmap.ACCESS_READ
        ) as owl_string:
            import_search = re.findall(import_tag, owl_string)  # type: ignore
            # mypy doesn't like re and mmap objects
            if len(import_search) > 0:
                for match in import_search:
                    imports.append(match.decode("utf-8"))
    except ValueError:  # Should not happen unless OWL definitions are missing/broken
        print("Could not parse OWL definitions enough to locate any imports.")

    return imports


def get_file_diff(before_filename, after_filename) -> str:
    """
    Get list of differences between two files, returned as a string.
    :param before_filename: str, name or path of first file
    :param after_filename: str, name or path of second file
    :return: str containing all lines different between the files
    """

    # Not currently called as it's too slow on large files
    # and the resulting large diffs are stored in memory.
    # TODO: replace with a call to shell diff -u

    diff_string = ""
    with open(before_filename, "r") as before_file:
        with open(after_filename, "r") as after_file:
            diff = difflib.unified_diff(
                before_file.readlines(),
                after_file.readlines(),
                fromfile=before_filename,
                tofile=after_filename,
            )
        for line in diff:
            diff_string = diff_string + line

    if diff_string == "":
        diff_string = "No difference"

    return diff_string


def get_file_length(filename) -> int:
    """
    Simple function to get number of lines in a file, as a string.
    Includes empty lines, too.
    :param filename: str, name or path of file
    :return: int containing count of lines in file
    """
    out_value = 0
    with open(filename, "r") as infile:
        for _ in infile:
            out_value = out_value + 1

    return out_value


def clean_and_normalize_graph(filename) -> bool:
    """
    Replace or remove node IDs or nodes as needed.
    Also replaces biolink:OntologyClass node types
    with biolink:NamedThing.
    :param filename: str, name or path of *compressed* KGX graph
    :return: bool, True if successful
    """

    success = True
    mapping = True

    graph_file_paths = []

    # Decompress graph
    with tarfile.open(filename) as intar:
        graph_files = intar.getnames()
        for graph_file in graph_files:
            intar.extract(graph_file, path=os.path.dirname(filename))
            graph_file_paths.append(os.path.join(os.path.dirname(filename), graph_file))
    os.remove(filename)

    # Remap node IDs
    # First, identify node and edge lists

    for filepath in graph_file_paths:
        if filepath.endswith("nodes.tsv"):
            nodepath = filepath
            outnodepath = nodepath + ".tmp"
        if filepath.endswith("edges.tsv"):
            edgepath = filepath
            outedgepath = edgepath + ".tmp"

    # Now load the update_id_map file
    id_map_path = os.path.join(os.path.dirname(filename), "update_id_maps.tsv")
    if not os.path.exists(id_map_path):
        print("Can't find ID remapping file. This may not be a problem.")
        mapping = False
    else:
        remap_these_nodes = {}
        with open(id_map_path) as map_file:
            map_file.readline()
            for line in map_file:
                splitline = line.rstrip().split("\t")
                cap_prefix = (
                    ((splitline[0].split(":"))[0].upper())
                    + ":"
                    + (splitline[0].split(":"))[1]
                )
                remap_these_nodes[splitline[0]] = splitline[1]
                remap_these_nodes[cap_prefix] = splitline[1]

    # Continue with mapping if everything's OK so far
    # Sometimes prefixes get capitalized, so we check for that too
    try:
        mapcount = 0
        with open(nodepath, "r") as innodefile, open(edgepath, "r") as inedgefile:
            with open(outnodepath, "w") as outnodefile, open(
                outedgepath, "w"
            ) as outedgefile:
                outnodefile.write(innodefile.readline())
                outedgefile.write(inedgefile.readline())
                for line in innodefile:
                    line_split = (line.rstrip()).split("\t")
                    if mapping:
                        # Check for nodes to be remapped
                        if line_split[0] in remap_these_nodes:
                            new_node_id = remap_these_nodes[line_split[0]]
                            line_split[0] = new_node_id
                            mapcount = mapcount + 1
                            line = "\t".join(line_split) + "\n"
                    if line_split[1] == "biolink:OntologyClass":
                        line_split[1] = "biolink:NamedThing"
                        line = "\t".join(line_split) + "\n"
                    outnodefile.write(line)
                for line in inedgefile:
                    line_split = (line.rstrip()).split("\t")
                    if mapping:
                        # Check for edges containing nodes to be remapped
                        for col in [1, 3]:
                            if line_split[col] in remap_these_nodes:
                                new_node_id = remap_these_nodes[line_split[col]]
                                line_split[col] = new_node_id
                                mapcount = mapcount + 1
                                line = "\t".join(line_split) + "\n"
                    outedgefile.write(line)

        os.replace(outnodepath, nodepath)
        os.replace(outedgepath, edgepath)

        if mapping and mapcount > 0:
            print(f"Remapped {mapcount} node IDs.")
        elif mapping and mapcount == 0:
            print("Failed to remap node IDs - could not find corresponding nodes.")
        
        success = True

    except (IOError, KeyError) as e:
        print(f"Failed to remap node IDs for {nodepath} and/or {edgepath}: {e}")
        for temppath in [outnodepath, outedgepath]:
            os.remove(temppath)
        success = False

    # Recompress graph
    with tarfile.open(filename, "w:gz") as outtar:
        for graph_file in graph_file_paths:
            outtar.add(graph_file, arcname=os.path.basename(graph_file))
            os.remove(graph_file)

    return success


def run_transform(
    skip: list = [],
    get_only: list = [],
    bucket="bucket",
    save_local=False,
    s3_test=False,
    no_dl_progress=False,
    force_index_refresh=False,
    replace_base_obos=False,
    robot_path: str = os.path.join(os.getcwd(), "robot"),
    lock_file_remote_path: str = "kg-obo/lock",
    force_overwrite=False,
    log_dir="logs",
    data_dir="data",
    remote_path="kg-obo",
    track_file_local_path: str = "data/tracking.yaml",
    tracking_file_remote_path: str = KGOBO_TRACK_FILE,
) -> bool:
    """
    Perform setup, then kgx-mediated transforms for all specified OBOs.
    :param skip: list of OBOs to skip, by ID
    :param get_only: list of OBOs to transform, by ID (otherwise do all)
    :param bucket: str of S3 bucket, to be specified as argument
    :param save_local: bool for whether to retain transform results on local disk
    :param s3_test: bool for whether to perform mock S3 upload only
    :param no_dl_progress: bool for whether to hide download progress bars
    :param force_index_refresh: bool for whether to rebuild all index.html on remote
    :param robot_path: str of path to robot, if different from default (bin/robot) - don't need '.jar' extension
    :param lock_file_remote_path: str of path for lock file on S3
    :param force_overwrite: bool, if True, will overwrite existing transform files on bucket
    :param log_dir: str of local dir where any logs should be saved
    :param data_dir: str of local dir where data should be saved
    :param remote_path: str of remote path on S3 bucket
    :param track_file_local_path: str of local path for tracking file
    :param tracking_file_remote_path: str of path of tracking file on S3
    :return: boolean indicating success or existing run encountered (False for unresolved error)
    """

    print("Setting up ROBOT...")
    if not robot_path:
        robot_path = os.path.join(os.getcwd(), "robot")
    robot_params = initialize_robot(robot_path)
    print(f"ROBOT path: {robot_path}")
    robot_env = robot_params[1]
    print(f"ROBOT evironment variables: {robot_env['ROBOT_JAVA_ARGS']}")

    if not robot_params[0]:  # i.e., if we couldn't find ROBOT
        sys.exit(
            "\t*** Could not locate ROBOT - ensure it is available and executable. \n\tExiting..."
        )

    # Set up logging
    timestring = (datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(log_dir, "obo_transform_" + timestring + ".log")
    log_level = logging.INFO
    log_format = "%(asctime)s [%(levelname)s]: %(message)s in %(pathname)s:%(lineno)d"

    root_logger_handler = logging.FileHandler(log_path)
    root_logger_handler.setFormatter(logging.Formatter(log_format))

    kg_obo_logger = logging.getLogger("kg-obo")
    kg_obo_logger.setLevel(log_level)
    kg_obo_logger.addHandler(root_logger_handler)

    kgx_logger = get_logger()
    kgx_logger.setLevel(log_level)
    kgx_logger.addHandler(root_logger_handler)

    # Set up CURIE checking and conversion converters
    # We need both maps for CURIE -> IRI (for validating) - this is curie_converter
    # and for IRI -> CURIE (for converting) - this is iri_converter
    # Note: not all prefixes in all_contexts are in all_reverse_contexts
    curie_contexts = load_multi_context(["obo", "bioregistry.upper"])
    all_contexts = curie_contexts.as_dict()
    all_contexts = {key: val for key, val in all_contexts.items()}
    curie_converter = Converter.from_prefix_map(all_contexts)
    all_reverse_contexts = {val: key for key, val in all_contexts.items()}
    all_reverse_contexts_lc = {val.lower(): key for key, val in all_contexts.items()}
    all_reverse_contexts.update(all_reverse_contexts_lc)
    all_reverse_contexts.update(KGOBO_PREFIXES)
    iri_converter = Converter.from_reverse_prefix_map(all_reverse_contexts)

    # Check if there's already a run in progress (i.e., lock file exists)
    # This isn't an error so it does not trigger an exit
    if s3_test:
        if kg_obo.upload.mock_check_lock(bucket, lock_file_remote_path):
            print("Could not mock checking for lock file. Exiting...")
            return True
    else:
        if kg_obo.upload.check_lock(bucket, lock_file_remote_path):
            print("A kg-obo run appears to be in progress. Exiting...")
            return True

    # Now set the lockfile
    if s3_test:
        if not kg_obo.upload.mock_set_lock(bucket, lock_file_remote_path, unlock=False):
            print("Could not mock setting lock file. Exiting...")
            return False
    else:
        if not kg_obo.upload.set_lock(bucket, lock_file_remote_path, unlock=False):
            print("Could not set lock file on remote server. Exiting...")
            return False

    # Check on existence of tracking file
    if s3_test:
        if not kg_obo.upload.mock_check_tracking(bucket, tracking_file_remote_path):
            print("Could not mock checking tracking file. Exiting...")
            return False
    else:
        if not kg_obo.upload.check_tracking(bucket, tracking_file_remote_path):
            print("Cannot locate tracking file on remote storage. Exiting...")
            return False

    if s3_test:
        upload_action = "simulate uploading"
    else:
        upload_action = "upload"
    print(f"Will {upload_action} using the following paths:")
    for item in [
        ("bucket", bucket),
        ("remote path", remote_path),
        ("local path", data_dir),
    ]:
        print(f"* {item[0]}: {item[1]}")

    # If requested, refresh the root index.html
    if force_index_refresh and not s3_test:
        print(f"Refreshing root index on {bucket}, {remote_path}")
        if kg_obo.upload.update_index_files(
            bucket, remote_path, data_dir, update_root=True
        ):
            kg_obo_logger.info(f"Refreshed root index at {remote_path}")
            print(f"Refreshed root index at {remote_path}")
        else:
            kg_obo_logger.info(f"Failed to refresh root index at {remote_path}")
            print(f"Failed to refresh root index at {remote_path}")
    elif force_index_refresh and s3_test:
        print(f"Mock refreshing root index on {bucket}, {remote_path}")
        if kg_obo.upload.mock_update_index_files(
            bucket, remote_path, data_dir, update_root=True
        ):
            kg_obo_logger.info(f"Mock refreshed root index at {remote_path}")
            print(f"Mock refreshed root index at {remote_path}")
        else:
            kg_obo_logger.info(f"Failed to mock refresh root index at {remote_path}")
            print(f"Failed to mock refresh root index at {remote_path}")

    # Get the OBO Foundry list YAML and process each
    yaml_onto_list_filtered = retrieve_obofoundry_yaml(skip=skip, get_only=get_only)

    successful_transforms = []
    errored_transforms = []
    failed_transforms = []
    all_completed_transforms = []
    all_obos_with_weird_version_formats = []

    if len(skip) > 0:
        kg_obo_logger.info(f"Ignoring these OBOs: {skip}")
    if save_local:
        kg_obo_logger.info("Will retain all downloaded files.")
    if s3_test:
        kg_obo_logger.info("Will test S3 upload instead of actually uploading.")

    for ontology in tqdm(yaml_onto_list_filtered, "processing ontologies"):
        ontology_name = ontology["id"]
        print(f"{ontology_name}")
        kg_obo_logger.info("Loading " + ontology_name)
        base_obo_path = os.path.join(data_dir, ontology_name)
        obo_remote_path = os.path.join(remote_path, ontology_name)

        # This will be true if the ontology will be replaced
        # even if the version has not changed since last upload
        replace_previous_transform = False

        # Get OBO URL
        url = kg_obo.obolibrary_utils.get_url(ontology_name)
        print(url)

        # Check if we may have previously used a base version of the OBO -
        # the base-obo's aren't really informative without reasoning,
        # so we'll overwrite them if they exist, and
        # if the replace_base_obos option was used.
        if replace_base_obos and kg_obo.obolibrary_utils.base_url_exists(ontology_name):
            replace_previous_transform = True

        # Set up local directories
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        # Downloaded OBOs are still tempfiles as we don't intend to keep them
        with tempfile.NamedTemporaryFile(prefix=ontology_name) as tfile:

            success = True

            # Some OBOs are quite large, so we download selection first to check IRI/version
            if not download_ontology(
                url=url,
                file=tfile.name,
                logger=kg_obo_logger,
                no_dl_progress=no_dl_progress,
                header_only=True,
            ):
                success = False
                kg_obo_logger.warning(
                    f"Failed to load due to KeyError: {ontology_name}"
                )
                failed_transforms.append(ontology_name)
                continue

            # Provide parsed IRI and version info here
            # If it wasn't in the versionIRI, add it to a list, because this is weird
            owl_iri, owl_version, owl_version_format = get_owl_iri(tfile.name)
            kg_obo_logger.info(f"Current VersionIRI for {ontology_name}: {owl_iri}")
            print(f"Current VersionIRI for {ontology_name}: {owl_iri}")
            kg_obo_logger.info(f"Current version for {ontology_name}: {owl_version}")
            print(f"Current version for {ontology_name}: {owl_version}")
            kg_obo_logger.info(
                f"In {ontology_name}, used this value for version: {owl_version_format}"
            )
            print(
                f"In {ontology_name}, used this value for version: {owl_version_format}"
            )
            if owl_version_format != "versionIRI":
                all_obos_with_weird_version_formats.append(ontology_name)

            # Check version here
            # If it's already in the tracking file, do nothing more with it
            # unless replace_previous_transform is True
            if (
                transformed_obo_exists(ontology_name, owl_iri, s3_test, bucket)
                and not replace_previous_transform
            ):
                kg_obo_logger.info(
                    f"Have already transformed {ontology_name}: {owl_iri}"
                )
                print(f"Have already transformed {ontology_name}: {owl_iri} - skipping")
                all_completed_transforms.append(ontology_name)

                # If requested, refresh the index.html even if we don't have a new version
                # This won't touch the individual version directories
                # Mock version isn't included here as we won't find existing versions under testing
                if force_index_refresh and not s3_test:
                    print(f"Refreshing index on {bucket} for {obo_remote_path}")
                    if kg_obo.upload.update_index_files(
                        bucket, obo_remote_path, data_dir
                    ):
                        kg_obo_logger.info(f"Refreshed index for {ontology_name}")
                        print(f"Refreshed index for {ontology_name}")
                    else:
                        kg_obo_logger.info(
                            f"Failed to refresh index for {ontology_name}"
                        )
                        print(f"Failed to refresh index for {ontology_name}")
                continue
            else:
                kg_obo_logger.info(
                    f"Don't have this version of {ontology_name} yet - will transform."
                )
                print(
                    f"Don't have this version of {ontology_name} yet - will transform."
                )

            # Check for imports, but don't retreive yet
            need_imports = False
            imports = imports_requested(tfile.name)
            if len(imports) > 0:
                fimports = ", ".join(imports)
                kg_obo_logger.info(
                    f"Header for {ontology_name} requests these imports: {fimports}"
                )
                print(f"Header for {ontology_name} requests these imports: {fimports}")
                need_imports = True
            else:
                kg_obo_logger.info(f"No imports found for {ontology_name}.")
                print(f"No imports found for {ontology_name}.")

            # Set up output folders for completed transform
            if not os.path.exists(base_obo_path):
                print(f"Making directory {base_obo_path}.")
                os.mkdir(base_obo_path)
            versioned_obo_path = os.path.join(base_obo_path, owl_version)
            if not os.path.exists(versioned_obo_path):
                print(f"Making directory {versioned_obo_path}.")
                os.mkdir(versioned_obo_path)

            # If this version is new, now we download the whole OBO
            # It starts as a temp file, but once we have the full version we
            # copy it to the same dir as where transforms will go
            if not download_ontology(
                url=url,
                file=tfile.name,
                logger=kg_obo_logger,
                no_dl_progress=no_dl_progress,
                header_only=False,
            ):
                success = False
                kg_obo_logger.warning(
                    f"Failed to load due to KeyError: {ontology_name}"
                )
                failed_transforms.append(ontology_name)
                continue
            else:
                orig_local_path = os.path.join(
                    versioned_obo_path, ontology_name + ".owl"
                )
                kg_obo_logger.info(f"Completed download from {url} to {tfile.name}.")
                print(f"Completed download from {url} to {tfile.name}.")
                kg_obo_logger.info(f"Moving from {tfile.name} to {orig_local_path}.")
                print(f"Moving from {tfile.name} to {orig_local_path}.")
                shutil.copy(tfile.name, orig_local_path)

            # Write the current KG-OBO git commit
            version_info_path = os.path.join(versioned_obo_path, "kg-obo_version")
            with open(version_info_path, "w") as version_info_file:
                repo = git.Repo(search_parent_directories=True)
                current_commit_hash = repo.head.object.hexsha
                version_info_file.write(current_commit_hash)

            # Run ROBOT preprocessing here - relax all, then do merge -> convert if needed
            kg_obo_logger.info(f"ROBOT preprocessing: relax {ontology_name}")
            print(f"ROBOT preprocessing: relax {ontology_name}")
            temp_suffix = f"_{ontology_name}_relaxed.owl"
            tfile_relaxed = tempfile.NamedTemporaryFile(
                delete=False, suffix=temp_suffix
            )
            if not relax_owl(robot_path, tfile.name, tfile_relaxed.name, robot_env):
                kg_obo_logger.error(
                    f"ROBOT relaxing of {ontology_name} failed - skipping."
                )
                print(f"ROBOT relaxing of {ontology_name} failed - skipping.")
                tfile_relaxed.close()
                continue
            tfile_relaxed.close()

            before_count = get_file_length(tfile.name)
            after_count = get_file_length(tfile_relaxed.name)
            kg_obo_logger.info(
                f"Before relax: {before_count} lines. After relax: {after_count} lines."
            )
            print(
                f"Before relax: {before_count} lines. After relax: {after_count} lines."
            )

            if after_count == 0:
                kg_obo_logger.error(
                    f"ROBOT relaxing of {ontology_name} yielded an empty result!"
                )
                print(f"ROBOT relaxing of {ontology_name} yielded an empty result!")
                continue  # Need to skip this one or we will upload empty results

            # If we have imports, merge+convert to resolve
            # Don't do this every time as it is not necessary
            # We don't convert to JSON just yet
            if need_imports:

                print(f"ROBOT preprocessing: merge and convert {ontology_name}")
                temp_suffix = f"_{ontology_name}_merged.owl"
                tfile_merged = tempfile.NamedTemporaryFile(
                    delete=False, suffix=temp_suffix
                )
                if not merge_and_convert_owl(
                    robot_path, tfile_relaxed.name, tfile_merged.name, robot_env
                ):
                    kg_obo_logger.error(
                        f"ROBOT merge of {ontology_name} failed - skipping."
                    )
                    print(f"ROBOT merge of {ontology_name} failed - skipping.")
                    tfile_relaxed.close()
                    continue
                tfile_merged.close()

                before_count = get_file_length(tfile_relaxed.name)
                after_count = get_file_length(tfile_merged.name)
                kg_obo_logger.info(
                    f"Before merge: {before_count} lines. After merge: {after_count} lines."
                )
                print(
                    f"Before merge: {before_count} lines. After merge: {after_count} lines."
                )

                if after_count == 0:
                    kg_obo_logger.error(
                        f"ROBOT merging of {ontology_name} yielded an empty result!"
                    )
                    print(f"ROBOT merging of {ontology_name} yielded an empty result!")
                    continue  # Need to skip this one or we will upload empty results

                input_owl = tfile_merged.name

            else:

                input_owl = tfile_relaxed.name

            # Get all ids from the input owl and identify normalized forms
            # We use this later to convert IDs
            print(f"ROBOT preprocessing: node ID normalization on {ontology_name}")
            if not examine_owl_names(
                robot_path,
                input_owl,
                versioned_obo_path,
                curie_converter,
                iri_converter,
                robot_env,
            ):
                kg_obo_logger.error(
                    f"ROBOT id retrieval for {ontology_name} failed - skipping."
                )
                print(f"ROBOT id retrieval for {ontology_name} failed - skipping.")

            # Convert to JSON
            print(f"ROBOT preprocessing: convert {ontology_name}")
            ontology_filename = f"{ontology_name}.json"
            owl_converted = os.path.join(versioned_obo_path, ontology_filename)
            if not convert_owl(
                robot_path, tfile_relaxed.name, owl_converted, robot_env
            ):
                kg_obo_logger.error(
                    f"ROBOT convert of {ontology_name} failed - skipping."
                )
                print(f"ROBOT convert of {ontology_name} failed - skipping.")
                tfile_relaxed.close()
                continue

            if not os.path.exists(owl_converted):
                kg_obo_logger.error(
                    f"ROBOT convert of {ontology_name} yielded no result!"
                )
                print(f"ROBOT convert of {ontology_name} yielded no result!")
                continue  # Need to skip this one or we will upload empty results

            input_owl = owl_converted

            # Use kgx to transform, but save errors to log
            # Do separate transforms for different output formats
            success = True  # for all transforms
            errors = False  # for all transforms
            output_format = "tsv"
            all_success_and_errors = {}
            print(f"Transforming {ontology_name} to {output_format}...")
            kg_obo_logger.info(f"Transforming to {output_format}...")
            if output_format == "tsv":
                ontology_filename = f"{ontology_name}_kgx_tsv"
            else:
                ontology_filename = f"{ontology_name}_kgx"
            this_success, this_errors, this_output_msg = kgx_transform(
                input_file=[input_owl],
                input_format="obojson",
                output_file=os.path.join(versioned_obo_path, ontology_filename),
                output_format=output_format,
                logger=kgx_logger,
                knowledge_sources=[
                    ("knowledge_source", f"{ontology_name.upper()} {owl_version}")
                ],
            )
            all_success_and_errors[output_format] = (this_success, this_errors)
            kg_obo_logger.info(this_output_msg)

            # Check results of all transforms
            if output_format == "tsv" and not all_success_and_errors[output_format][0]:
                success = False
            if all_success_and_errors[output_format][1]:
                errors = True
                break

            # Time for post-processing.
            print(f"Post-processing {ontology_name}...")
            kg_obo_logger.info(f"Post-processing {ontology_name}...")
            input_file = os.path.join(versioned_obo_path, ontology_filename + ".tar.gz")
            if not clean_and_normalize_graph(input_file):
                success = False
                print(f"Failed post-processing {ontology_name}...")
                kg_obo_logger.info(f"Failed post-processing {ontology_name}...")

            # Check file size and fail/warn if nodes|edge file is empty
            for filename in os.listdir(versioned_obo_path):
                if filename.endswith(".tar.gz"):
                    filesize = os.stat(
                        os.path.join(versioned_obo_path, filename)
                    ).st_size
                    if filesize < 400:
                        kg_obo_logger.warning(
                            f"{filename} appears to contain empty graph files - something went wrong."
                        )
                        print(f"{filename} appears to contain empty graph files - something went wrong.")
                        success = False

            if success and not errors:
                kg_obo_logger.info(
                    f"Successfully completed transform of {ontology_name}"
                )
                successful_transforms.append(ontology_name)
                all_completed_transforms.append(ontology_name)

            elif success and errors:
                kg_obo_logger.info(
                    f"Completed transform of {ontology_name} with errors - see logs for details."
                )
                errored_transforms.append(ontology_name)
                all_completed_transforms.append(ontology_name)
            else:
                kg_obo_logger.warning(f"Failed to transform {ontology_name}")
                failed_transforms.append(ontology_name)

            if success:
                versioned_remote_path = os.path.join(
                    remote_path, ontology_name, owl_version
                )
                if not s3_test:
                    # Write to remote tracking file
                    kg_obo_logger.info(
                        f"Adding {ontology_name} version {owl_version} to tracking file."
                    )
                    track_obo_version(ontology_name, owl_iri, owl_version, bucket)

                    # Upload the most recently transformed version to bucket
                    # Include the original OWL too (this already happens because it's in the new dir)
                    # Include the current KG-OBO git commit (ditto)
                    # Also verify that files have the expected name format
                    kg_obo_logger.info(
                        f"Uploading {versioned_obo_path} to {versioned_remote_path}..."
                    )
                    filelist = kg_obo.upload.upload_dir_to_s3(
                        versioned_obo_path,
                        bucket,
                        versioned_remote_path,
                        make_public=True,
                        force_overwrite=force_overwrite
                    )
                    if not kg_obo.upload.verify_uploads(filelist, ontology_name):
                        kg_obo_logger.info(
                            f"Transform filenames for {ontology_name} and {owl_version} are incorrect!"
                        )

                    # Update indexes for this version and OBO only
                    if kg_obo.upload.update_index_files(
                        bucket, versioned_remote_path, data_dir
                    ) and kg_obo.upload.update_index_files(
                        bucket, obo_remote_path, data_dir
                    ):
                        kg_obo_logger.info(
                            f"Created index for {ontology_name} and {owl_version}"
                        )
                    else:
                        kg_obo_logger.info(
                            f"Failed to create index for {ontology_name} and {owl_version}"
                        )

                else:
                    kg_obo_logger.info(
                        f"Mock uploading {versioned_obo_path} to {versioned_remote_path}..."
                    )
                    filelist = kg_obo.upload.mock_upload_dir_to_s3(
                        versioned_obo_path,
                        bucket,
                        versioned_remote_path,
                        make_public=True,
                    )
                    if not kg_obo.upload.verify_uploads(filelist, ontology_name):
                        kg_obo_logger.info(
                            f"Transform filenames for {ontology_name} and {owl_version} are incorrect!"
                        )

                    if kg_obo.upload.mock_update_index_files(
                        bucket, versioned_remote_path, data_dir
                    ) and kg_obo.upload.mock_update_index_files(
                        bucket, obo_remote_path, data_dir
                    ):
                        kg_obo_logger.info(
                            f"Mock created index for {ontology_name} and {owl_version}"
                        )
                    else:
                        kg_obo_logger.info(
                            f"Failed to mock create index for {ontology_name} and {owl_version}"
                        )

            # Clean up any incomplete transform leftovers
            if not success and not save_local:
                if delete_path(base_obo_path):
                    kg_obo_logger.info(
                        f"Removed incomplete transform files for {ontology_name}."
                    )
                else:
                    kg_obo_logger.warning(
                        f"Incomplete version of {ontology_name} may be present."
                    )

    kg_obo_logger.info(
        f"Successfully transformed {len(successful_transforms)} without errors: {successful_transforms}"
    )

    if len(errored_transforms) > 0:
        kg_obo_logger.info(
            f"Successfully transformed {len(errored_transforms)} with errors: {errored_transforms}"
        )

    if len(failed_transforms) > 0:
        kg_obo_logger.info(
            f"Failed to transform {len(failed_transforms)}: {failed_transforms}"
        )

    if len(all_completed_transforms) > 0:
        kg_obo_logger.info(
            f"All available transforms, including old versions ({len(all_completed_transforms)}): "
            f"{all_completed_transforms}"
        )

    if len(all_obos_with_weird_version_formats) > 0:
        kg_obo_logger.info(
            f"These OBOs have versions stored in places other than versionIRI ({len(all_obos_with_weird_version_formats)}): "
            f"{all_obos_with_weird_version_formats}"
        )

    if not s3_test:
        # Update the root index
        if kg_obo.upload.update_index_files(
            bucket, remote_path, data_dir, update_root=True
        ):
            kg_obo_logger.info(f"Updated root index at {remote_path}")
            print(f"Updated root index at {remote_path}")
        else:
            kg_obo_logger.info(f"Failed to update root index at {remote_path}")
            print(f"Failed to update root index at {remote_path}")
    else:
        if kg_obo.upload.mock_update_index_files(
            bucket, remote_path, data_dir, update_root=True
        ):
            kg_obo_logger.info(f"Mock updated root index at {remote_path}")
            print(f"Mock updated root index at {remote_path}")
        else:
            kg_obo_logger.info(f"Failed to mock update root index at {remote_path}")
            print(f"Failed to mock update root index at {remote_path}")

    # Remove all local data files
    if not save_local:
        if delete_path(data_dir, omit=[track_file_local_path]):
            kg_obo_logger.info(f"Removed local data from {data_dir}.")
        else:
            kg_obo_logger.warning(f"Local data not deleted from {data_dir}.")

    # Now un-set the lockfile
    if s3_test:
        if not kg_obo.upload.mock_set_lock(bucket, lock_file_remote_path, unlock=True):
            sys.exit("Could not mock setting lock file. Exiting...")
    else:
        if not kg_obo.upload.set_lock(bucket, lock_file_remote_path, unlock=True):
            sys.exit("Could not set lock file on remote server. Exiting...")

    return True
