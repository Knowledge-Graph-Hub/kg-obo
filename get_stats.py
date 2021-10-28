#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Get details about the OBO graphs currently available on KG-OBO.
"""

import click  #type: ignore
import sys
from kg_obo.stats import get_graph_stats

@click.command()
@click.option("--skip",
               callback=lambda _,__,x: x.split(',') if x else [],
               help="One or more OBOs to ignore, comma-delimited and named by their IDs, e.g., bfo.")
@click.option("--get_only",
               callback=lambda _,__,x: x.split(',') if x else [],
               help="""One or more OBOs to retreive, and only these,
                     comma-delimited and named by their IDs, e.g., bfo.""")
@click.option("--bucket",
               required=True,
               nargs=1,
               help="""The name of the AWS S3 bucket to retrieve nodes/edges from.""")
def run(skip, get_only, bucket):
    try:
        if get_graph_stats(skip, get_only, bucket): 
            print("Operation completed without errors.")
        else:
            print("Operation did not complete successfully.")
    except Exception as e:
        print(f"Encountered unresolvable error: {type(e)} - {e} ({e.args})")
        sys.exit(1)

if __name__ == '__main__':
  run()
