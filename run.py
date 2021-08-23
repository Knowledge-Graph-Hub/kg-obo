#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Transform all available OBO Foundry ontologies from OBO format
to KGX TSV, with intermediate JSON.
"""

import tempfile
from kgx.cli import transform  # type: ignore
from tqdm import tqdm  # type: ignore
import yaml  # type: ignore
import requests  # type: ignore
from datetime import datetime
import os
import logging

from xml.sax._exceptions import SAXParseException

from kg_obo.obolibrary_utils import base_url_if_exists

# Set up logging
timestring = (datetime.now()).strftime("%Y-%m-%d_%H%M%S")
logging.basicConfig(filename="obo_transform_" + timestring + ".log",
                    level=logging.NOTSET
                    )

# this is a stable URL containing a YAML file that describes all the OBO ontologies:
# get the ID for each ontology, construct PURL

source_of_obo_truth = 'https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml'
path_to_robot = "/usr/local/bin/"

yaml_req = requests.get(source_of_obo_truth)
yaml_content = (yaml_req.content).decode('utf-8')
yaml_parsed = yaml.safe_load(yaml_content)

for ontology in tqdm(yaml_parsed['ontologies'], "processing ontologies"):
    ontology_name = ontology['id']
    print(f"{ontology_name}")
    logging.info("Loading " + ontology_name)

    url = base_url_if_exists(ontology_name)  # take base ontology if it exists, otherwise just use non-base
    print(url)

    # TODO: generate base if it doesn't exist, using robot

    # download url to tempfile
    # use kgx to convert OWL to KGX tsv
    with tempfile.NamedTemporaryFile(prefix=ontology_name) as tfile:
        req = requests.get(url, stream=True)
        file_size = int(req.headers['Content-Length'])
        chunk_size = 1024
        with open(tfile.name, 'wb') as outfile:
            pbar = tqdm(unit="B", total=file_size, unit_scale=True, unit_divisor=chunk_size)
            for chunk in req.iter_content(chunk_size=chunk_size):
                if chunk:
                    pbar.update(len(chunk))
                    outfile.write(chunk)
        pbar.close()
        
        tf_output_dir = tempfile.mkdtemp(prefix=ontology_name)
        
        try:
            transform(inputs=[tfile.name],
                input_format='owl',
                output=os.path.join(tf_output_dir, ontology_name),
                output_format='tsv',
                )
        except FileNotFoundError as e:
            logging.error(e)
        except SAXParseException as e:
            logging.error(e)

    # query kghub/[ontology]/current/*hash*
    
    # kghub/obo2kghub/bfo/2021_08_16|current/nodes|edges.tsv|date-hash
    os.system(f"ls -lhd {tf_output_dir}/*")
    # upload to S3
