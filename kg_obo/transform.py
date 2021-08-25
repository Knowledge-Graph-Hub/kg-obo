import tempfile
import kgx

from kgx.config import get_logger # type: ignore
from tqdm import tqdm  # type: ignore
import yaml  # type: ignore
import requests  # type: ignore
from datetime import datetime
import os
import logging

from xml.sax._exceptions import SAXParseException  # type: ignore
from rdflib.exceptions import ParserError # type: ignore

from kg_obo.obolibrary_utils import base_url_if_exists


def retrieve_obofoundry_yaml(
        yaml_url: str = 'https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml',
        skip_list: list = []) -> list:
    """ Retrieve YAML containing list of all ontologies in OBOFoundry
    :param yaml_url: a stable URL containing a YAML file that describes all the OBO ontologies:
    :param skip_list: which ontologies should we skip
    :return: parsed yaml describing ontologies to transform
    """
    yaml_req = requests.get(yaml_url)
    yaml_content = yaml_req.content.decode('utf-8')
    yaml_parsed = yaml.safe_load(yaml_content)
    if not yaml_parsed or 'ontologies' not in yaml_parsed:
        raise RuntimeError(f"Can't retrieve ontology info from YAML at this url {yaml_url}")
    else:
        yaml_onto_list: list = yaml_parsed['ontologies']
    yaml_onto_list_filtered = \
        [ontology for ontology in yaml_onto_list if ontology['id'] not in skip_list]
    return yaml_onto_list_filtered


def kgx_transform(input_file: list, input_format: str,
                  output_file: str, output_format: str, logger: object) -> bool:
    """Call KGX transform and report success status (bool)

    :param input_file: list of files to transform
    :param input_format: input format
    :param output_file: output file root (appended with nodes/edges.[format])
    :param output_format: output format
    :param logger: logger
    :return: boolean - did transform work?
    """
    success = True
    try:
        kgx.cli.transform(inputs=input_file,
                          input_format=input_format,
                          output=output_file,
                          output_format=output_format)
    except (FileNotFoundError,
            SAXParseException,
            ParserError,
            Exception) as e:
        success = False
        logger.error(e, f"KGX problem while transforming {input_file}")  # type: ignore
    return success


def run_transform(skip_list: list = [], log_dir="logs") -> None:

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
    yaml_onto_list_filtered = retrieve_obofoundry_yaml(skip_list=skip_list)

    for ontology in tqdm(yaml_onto_list_filtered, "processing ontologies"):
        ontology_name = ontology['id']
        print(f"{ontology_name}")
        kg_obo_logger.info("Loading " + ontology_name)

        # take base ontology if it exists, otherwise just use non-base
        url = base_url_if_exists(ontology_name)
        print(url)

        # download url to tempfile
        # use kgx to convert OWL to KGX tsv
        with tempfile.NamedTemporaryFile(prefix=ontology_name) as tfile:

            success = True
            try:
                req = requests.get(url, stream=True)
                file_size = int(req.headers['Content-Length'])
                chunk_size = 1024
                with open(tfile.name, 'wb') as outfile:
                    pbar = tqdm(unit="B", total=file_size, unit_scale=True,
                                unit_divisor=chunk_size)
                    for chunk in req.iter_content(chunk_size=chunk_size):
                        if chunk:
                            pbar.update(len(chunk))
                            outfile.write(chunk)
            except KeyError as e:
                kg_obo_logger.error(e)
                success = False
                kg_obo_logger.warning("Encountered errors while transforming " + ontology_name)
                continue

            pbar.close()

            tf_output_dir = tempfile.mkdtemp(prefix=ontology_name)

            # Use kgx to transform, but save errors to log
            success = kgx_transform(input_file=[tfile.name],
                                    input_format='owl',
                                    output_file=os.path.join(tf_output_dir, ontology_name),
                                    output_format='tsv',
                                    logger=kg_obo_logger)

            # TODO: check file size and fail/warn if nodes|edge file is empty

            if success:
                kg_obo_logger.info("Successfully completed transform of " + ontology_name)
            else:
                kg_obo_logger.warning("Encountered errors while transforming " + ontology_name)

            # query kghub/[ontology]/current/*hash*

        # kghub/obo2kghub/bfo/2021_08_16|current/nodes|edges.tsv|date-hash
        os.system(f"ls -lhd {tf_output_dir}/*")

        # upload to S3
