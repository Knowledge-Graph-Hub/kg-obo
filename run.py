#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Transform all available OBO Foundry ontologies from OBO format
to KGX TSV, with intermediate JSON.
"""

import click  #type: ignore
from kg_obo.transform import run_transform

@click.command()
@click.option("--skip",
               callback=lambda _,__,x: x.split(',') if x else [],
               help="One or more OBOs to ignore, comma-delimited and named by their IDs, e.g., bfo.")
@click.option("--bucket",
               default="",
               nargs=1,
               help="The name of an AWS S3 bucket to upload transforms to.")
@click.option("--local",
               type=click.Path(),
               is_flag=True,
               help="If used, saves all transforms, tracking file, and index files to a local_data directory.")
def run(skip, bucket, local):
  run_transform(skip,bucket,local)

if __name__ == '__main__':
  run()
