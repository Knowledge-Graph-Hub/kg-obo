#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run a KGX transform from OBO OWL to node/edgelists only.
"""

import kg_obo
import click  #type: ignore
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
    kg_obo.transform.kgx_transform(input_file=[input_file], 
                                input_format='owl',
                                output_file=output_file,
                                output_format='tsv', 
                                logger=kgx_logger)

if __name__ == '__main__':
  run()