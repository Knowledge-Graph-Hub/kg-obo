#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Transform all available OBO Foundry ontologies from OBO format
to KGX TSV, with intermediate JSON.
"""

import click  #type: ignore
import os
import sys
from pathlib import Path
from kg_obo.transform import run_transform

@click.command()
@click.option("--skip",
               callback=lambda _,__,x: x.split(',') if x else [],
               help="One or more OBOs to ignore, comma-delimited and named by their IDs, e.g., bfo.")
@click.option("--get_only",
               callback=lambda _,__,x: x.split(',') if x else [],
               help="""One or more OBOs to retreive and transform, and only these,
                     comma-delimited and named by their IDs, e.g., bfo.""")
@click.option("--bucket",
               default="",
               nargs=1,
               help="The name of an AWS S3 bucket to upload transforms to.")
@click.option("--save_local",
               is_flag=True,
               help="""If used, keeps all transforms, tracking file, and index files in the directory.
                     Otherwise, they are deleted.""")
@click.option("--s3_test",
               is_flag=True,
               help="If used, upload to S3 bucket is tested only.")
def run(skip, get_only, bucket, save_local, s3_test):
    if os.path.isfile("lock"):
        sys.exit("KG-OBO is already running. Exiting...")
    else:
        Path("lock").touch()
        run_transform(skip, get_only, bucket, save_local, s3_test)
        os.remove("lock")

if __name__ == '__main__':
  run()
