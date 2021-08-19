#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Transform all available OBO Foundry ontologies from OBO format
to KGX TSV, with intermediate JSON.
"""

import tempfile
from kgx.cli import transform
from tqdm import tqdm
import yaml
import urllib.request
import os

# ROBOT needs to be installed beforehand
from kg_obo.obolibrary_utils import base_url_if_exists
from kg_obo.robot_utils import initialize_robot, convert_owl_to_json

initialize_robot("/usr/local/bin")

# this is a stable URL containing a YAML file that describes all the OBO ontologies:
# get the ID for each ontology, construct PURL
from robot_utils import convert_owl_to_json

source_of_obo_truth = 'https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml'
path_to_robot = "/usr/local/bin/"

with urllib.request.urlopen(source_of_obo_truth) as f:
    yaml_content = f.read().decode('utf-8')
    yaml_parsed = yaml.safe_load(yaml_content)


for ontology in tqdm(yaml_parsed['ontologies'], "processing ontologies"):
    ontology_name = ontology['id']
    print(f"{ontology_name}")

    url = base_url_if_exists(ontology_name)  # take base ontology if it exists, otherwise just use non-base
    # TODO: generate base if it doesn't exist, using robot

    tf_input = tempfile.NamedTemporaryFile(prefix=ontology_name)
    tf_output_dir = tempfile.TemporaryDirectory()

    # download url
    urllib.request.urlretrieve(url, tf_input.name)

    # query kghub/[ontology]/current/*hash*

    # convert from owl to json using ROBOT

    json_file = convert_owl_to_json(path_to_robot, tf_input.name)

    # use kgx to convert OWL to KGX tsv
    transform(inputs=[json_file],
              input_format='json',
              output=os.path.join(tf_output_dir.name, ontology_name),
              output_format='tsv',
              )

    # kghub/obo2kghub/bfo/2021_08_16|current/nodes|edges.tsv|date-hash
    os.system(f"ls -lhd {tf_output_dir.name}/*")
    # upload to S3
