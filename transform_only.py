#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run a KGX transform from OBO OWL to node/edgelists only.
"""

import kg_obo
from kg_obo.robot_utils import initialize_robot, relax_owl, merge_and_convert_owl

import click  #type: ignore
import os
import logging

kgx_logger = logging.getLogger("kg-obo")

@click.command()
@click.option("--input_file",
               required=True,
               nargs=1,
               help="""Path to an input file in OWL format.""")
@click.option("--output_file",
               required=True,
               nargs=1,
               help="""Name of a compressed output file to be created in KGX format""")
def run(input_file, output_file):

    robot_path = os.path.join(os.getcwd(),"robot")
    robot_params = initialize_robot(robot_path)
    robot_env = robot_params[1]

    relaxed_file = os.path.splitext(input_file)[0]+'_relaxed.owl'

    if not relax_owl(robot_path, input_file, relaxed_file, robot_env):
                print(f"ROBOT relaxing of {input_file} failed!")

    kg_obo.transform.kgx_transform(input_file=[relaxed_file], 
                                input_format='owl',
                                output_file=output_file,
                                output_format='tsv', 
                                logger=kgx_logger)

if __name__ == '__main__':
  run()