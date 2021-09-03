import tempfile
import kgx.cli  # type: ignore
from kgx.config import get_logger # type: ignore
from tqdm import tqdm  # type: ignore
import yaml  # type: ignore
import requests  # type: ignore
from datetime import datetime
import os
import shutil
import logging
import mmap
import re

from xml.sax._exceptions import SAXParseException  # type: ignore
from rdflib.exceptions import ParserError # type: ignore

import kg_obo.obolibrary_utils
import kg_obo.upload

def retrieve_obofoundry_yaml(
        yaml_url: str = 'https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml',
        skip: list = [],
        get_only: list = []) -> list:
    """ Retrieve YAML containing list of all ontologies in OBOFoundry
    :param yaml_url: a stable URL containing a YAML file that describes all the OBO ontologies:
    :param skip: which ontologies should we skip
    :return: parsed yaml describing ontologies to transform
    """
    yaml_req = requests.get(yaml_url)
    yaml_content = yaml_req.content.decode('utf-8')
    yaml_parsed = yaml.safe_load(yaml_content)
    if not yaml_parsed or 'ontologies' not in yaml_parsed:
        raise RuntimeError(f"Can't retrieve ontology info from YAML at this url {yaml_url}")
    else:
        yaml_onto_list: list = yaml_parsed['ontologies']
    
    if len(skip) > 0:
        yaml_onto_list_filtered = \
            [ontology for ontology in yaml_onto_list if ontology['id'] not in skip \
            if ("is_obsolete" not in ontology) or (ontology['is_obsolete'] == False)
            ]
    elif len(get_only) > 0:
        yaml_onto_list_filtered = \
            [ontology for ontology in yaml_onto_list if ontology['id'] in get_only \
            if ("is_obsolete" not in ontology) or (ontology['is_obsolete'] == False)
            ]    
    else:
        yaml_onto_list_filtered = \
            [ontology for ontology in yaml_onto_list \
            if ("is_obsolete" not in ontology) or (ontology['is_obsolete'] == False)
            ]

    return yaml_onto_list_filtered


def kgx_transform(input_file: list, input_format: str,
                  output_file: str, output_format: str, logger: object) -> tuple:
    """Call KGX transform and report success status (bool)

    :param input_file: list of files to transform
    :param input_format: input format
    :param output_file: output file root (appended with nodes/edges.[format])
    :param output_format: output format
    :param logger: logger
    :return: tuple - (bool for did transform work?, bool for any errors encountered)
    """
    success = True
    errors = False
    try:
        kgx.cli.transform(inputs=input_file,
                          input_format=input_format,
                          output=output_file,
                          output_format=output_format)
        if hasattr(logger, "_cache") and 30 in logger._cache and logger._cache[30]:  # type: ignore
            logger.error("Encountered errors in transforming or parsing.")  # type: ignore
            errors = True
            logger._cache.clear()  # type: ignore
    except (FileNotFoundError,
            SAXParseException,
            ParserError,
            Exception) as e:
        success = False
        logger.error(e, f"KGX problem while transforming {input_file}")  # type: ignore
    return (success, errors)

def get_owl_iri(input_file_name: str) -> tuple:
    """
    Extracts version IRI from OWL definitions.
    Here, the IRI is the full URL of the origin OWL, 
    as naming conventions vary.
    Avoids much file parsing as the IRI should be near the top of the file.
    Does some string parsing to get a shorter version number.
    Versions may take multiple formats across OBOs.

    :param input_file_name: name of OWL format file to extract IRI from
    :return: tuple of (str of IRI, str of version)
    """
    
    iri_tag = b'owl:versionIRI rdf:resource=\"(.*)\"'
    
    iri = "NA"
    version = "release"

    try:
        with open(input_file_name, 'rb', 0) as owl_file, \
            mmap.mmap(owl_file.fileno(), 0, access=mmap.ACCESS_READ) as owl_string:
            iri_search = re.search(iri_tag, owl_string) #type: ignore
            #mypy doesn't like re and mmap objects
            if iri_search:
                iri = (iri_search.group(1)).decode("utf-8")
                try:
                    version = (iri.split("/"))[-2]
                except IndexError:
                    pass
            else:
                print("Version IRI not found.")
    except ValueError: #Should not happen unless OWL definitions are missing/broken
        print("Could not parse OWL definitions enough to locate version IRI.")
       
    return (iri, version)

def track_obo_version(name: str = "", iri: str = "", version: str = "") -> None:
    """
    Writes OBO version as per IRI to tracking.yaml.
    
    :param name: name of OBO, as OBO ID
    :param iri: full OBO VersionIRI, as URL
    :param version: short OBO version
    """

    tracking_path = os.path.join("data", "tracking.yaml")
   
    with open(tracking_path, 'r') as track_file:
        tracking = yaml.load(track_file, Loader=yaml.BaseLoader)
    
    #If we already have a version, move it to archive
    if tracking["ontologies"][name]["current_version"] != "NA":
        if "archive" not in tracking["ontologies"][name]:
            tracking["ontologies"][name] = []
        tracking["ontologies"][name]["archive"].append({"iri": iri, "version": version})
    else:
        tracking["ontologies"][name]["current_iri"] = iri
        tracking["ontologies"][name]["current_version"] = version

    with open(tracking_path, 'w') as track_file:
        track_file.write(yaml.dump(tracking))

def transformed_obo_exists(name: str, iri: str) -> bool:
    """
    Read tracking.yaml to determine if transformed version of this OBO exists.
    
    :param name: string of short logger name, e.g., bfo
    :param iri: iri of OBO version
    :return: boolean, True if this OBO and version already exist as transformed
    """
    
    tracking_path = os.path.join("data", "tracking.yaml")
    
    with open(tracking_path, 'r') as track_file:
        tracking = yaml.load(track_file, Loader=yaml.BaseLoader)
    
    #We only check the most recent version - if we are transforming an old version,
    #then let it happen
    if tracking["ontologies"][name]["current_iri"] == iri:
        return True
    else:
        return False

def download_ontology(url: str, file: str, logger: object) -> bool:
    """
    Download ontology from URL

    :param url: url to download from
    :param file: file to download into
    :param logger:
    :return: boolean indicating whether download worked
    """
    try:
        req = requests.get(url, stream=True)
        file_size = int(req.headers['Content-Length'])
        chunk_size = 1024
        with open(file, 'wb') as outfile:
            pbar = tqdm(unit="B", total=file_size, unit_scale=True,
                        unit_divisor=chunk_size)
            for chunk in req.iter_content(chunk_size=chunk_size):
                if chunk:
                    pbar.update(len(chunk))
                    outfile.write(chunk)
        return True
    except KeyError as e:
        logger.error(e)  # type: ignore
        return False

def run_transform(skip: list = [], get_only: list = [], bucket="", local=False, s3_test=False,
                  log_dir="logs", data_dir="data") -> None:
    
    # Set up logging
    timestring = (datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(log_dir, "obo_transform_" + timestring + ".log")
    log_level = logging.INFO
    log_format = ("%(asctime)s [%(levelname)s]: %(message)s in %(pathname)s:%(lineno)d")

    root_logger_handler = logging.FileHandler(log_path)
    root_logger_handler.setFormatter(logging.Formatter(log_format))

    kg_obo_logger = logging.getLogger("kg-obo")
    kg_obo_logger.setLevel(log_level)
    kg_obo_logger.addHandler(root_logger_handler)

    kgx_logger = get_logger()
    kgx_logger.setLevel(log_level)
    kgx_logger.addHandler(root_logger_handler)

    # Get the OBO Foundry list YAML and process each
    yaml_onto_list_filtered = retrieve_obofoundry_yaml(skip=skip, get_only=get_only)

    successful_transforms = []
    errored_transforms = []
    failed_transforms = []
    
    if len(skip) >0:
      kg_obo_logger.info(f"Ignoring these OBOs: {skip}" ) 
    if local:
      kg_obo_logger.info("Will retain all downloaded files.")
    if s3_test:
      kg_obo_logger.info("Will test S3 upload instead of actually uploading.")

    for ontology in tqdm(yaml_onto_list_filtered, "processing ontologies"):
        ontology_name = ontology['id']
        print(f"{ontology_name}")
        kg_obo_logger.info("Loading " + ontology_name)

        # take base ontology if it exists, otherwise just use non-base
        url = kg_obo.obolibrary_utils.base_url_if_exists(ontology_name)
        print(url)

        # download url
        # use kgx to convert OWL to KGX tsv
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)
        base_obo_path = os.path.join(data_dir, ontology_name)
        if not os.path.exists(base_obo_path):
            os.mkdir(base_obo_path)
        
        # Downloaded OBOs are still tempfiles as we don't intend to keep them
        with tempfile.NamedTemporaryFile(prefix=ontology_name) as tfile:

            success = True

            if not download_ontology(url=url, file=tfile.name, logger=kg_obo_logger):
                success = False
                kg_obo_logger.warning(f"Failed to load due to KeyError: {ontology_name}")
                failed_transforms.append(ontology_name)
                continue
            
            owl_iri, owl_version = get_owl_iri(tfile.name)
            kg_obo_logger.info(f"Current VersionIRI for {ontology_name}: {owl_iri}") 
            print(f"Current VersionIRI for {ontology_name}: {owl_iri}")

            #Check version here
            if transformed_obo_exists(ontology_name, owl_iri):
                kg_obo_logger.info(f"Have already transformed {ontology_name}: {owl_iri}")
                print(f"Have already transformed {ontology_name}: {owl_iri} - skipping")
                continue

            versioned_obo_path = os.path.join(base_obo_path, owl_version)
            if not os.path.exists(versioned_obo_path):
                os.mkdir(versioned_obo_path)

            # Use kgx to transform, but save errors to log
            transform_errors: list = []
            success, errors = kgx_transform(input_file=[tfile.name],
                                            input_format='owl',
                                            output_file=os.path.join(versioned_obo_path, ontology_name),
                                            output_format='tsv',
                                            logger=kgx_logger)

            # Check file size and fail/warn if nodes|edge file is empty
            for filename in os.listdir(versioned_obo_path):
              if os.stat(os.path.join(versioned_obo_path, filename)).st_size == 0:
                  kg_obo_logger.warning("Output is empty - something went wrong during transformation.")
                  success = False
              else:
                  kg_obo_logger.info(f"{filename} {os.stat(os.path.join(versioned_obo_path, filename)).st_size} bytes")

            if success and not errors:
                kg_obo_logger.info(f"Successfully completed transform of {ontology_name}")
                successful_transforms.append(ontology_name)

                track_obo_version(ontology_name, owl_iri, owl_version)

                kg_obo.upload.upload_index_files(ontology_name, versioned_obo_path)
                
                kg_obo_logger.info("Uploading...")
                if bucket != "":
                    if not s3_test:
                        kg_obo.upload.upload_dir_to_s3("data",bucket,"data", make_public=False)
                    else:
                        kg_obo.upload.mock_upload_dir_to_s3("data",bucket,"data", make_public=False)
                else:
                    kg_obo_logger.info("Bucket name not provided. Not uploading.")
                
                if not local:
                    for filename in os.listdir(data_dir):
                        file_path = os.path.join(data_dir, filename)
                        if filename != "tracking.yaml":
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)

            elif success and errors:
                kg_obo_logger.info(f"Completed transform of {ontology_name} with errors")
                errored_transforms.append(ontology_name)
            else:
                kg_obo_logger.warning(f"Failed to transform {ontology_name}")
                failed_transforms.append(ontology_name)

    kg_obo_logger.info(f"Successfully transformed {len(successful_transforms)}: {successful_transforms}")

    if len(errored_transforms) > 0:
        kg_obo_logger.info(f"Incompletely transformed due to errors {len(errored_transforms)}: {errored_transforms}")

    if len(failed_transforms) > 0:
        kg_obo_logger.info(f"Failed to transform {len(failed_transforms)}: {failed_transforms}")

