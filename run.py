#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Transform all available OBO Foundry ontologies from OBO format
to KGX TSV, with intermediate JSON.
"""

import click  #type: ignore
import sys
from kg_obo.transform import run_transform
import kg_obo.upload

@click.command()
@click.option("--skip",
               callback=lambda _,__,x: x.split(',') if x else [],
               help="One or more OBOs to ignore, comma-delimited and named by their IDs, e.g., bfo.")
@click.option("--get_only",
               callback=lambda _,__,x: x.split(',') if x else [],
               help="""One or more OBOs to retreive and transform, and only these,
                     comma-delimited and named by their IDs, e.g., bfo.""")
@click.option("--bucket",
               required=True,
               nargs=1,
               help="""The name of an AWS S3 bucket to upload transforms to.
                     Can be anything if the s3_test option is set.""")
@click.option("--save_local",
               is_flag=True,
               help="""If used, keeps all transforms, tracking file, and index files in the directory.
                     Otherwise, they are deleted.""")
@click.option("--s3_test",
               is_flag=True,
               help="If used, upload to S3 bucket is tested only and false credentials are used.")
@click.option("--no_dl_progress",
               is_flag=True,
               help="If used, progress bar output is suppressed. Makes for nicer build output.")
@click.option("--force_index_refresh",
               is_flag=True,
               help="If used, rebuilds root index.html before beginning any transforms.")
@click.option("--replace_base_obos",
               is_flag=True,
               help="""If used, retrieves a new non-base version of each OBO if base was previously used,
                     even if the version name has not changed.""")
@click.option("--robot_path",
               nargs=1,
               help="""The path to robot.jar. Use only if other than kg-obo directory.""")
def run(skip, get_only, bucket, save_local, s3_test, no_dl_progress, force_index_refresh, replace_base_obos,
        robot_path):
    lock_file_remote_path = "kg-obo/lock"
    try:
        if run_transform(skip, get_only, bucket, save_local, s3_test, no_dl_progress, 
                         force_index_refresh, replace_base_obos, robot_path, lock_file_remote_path):
            print("Operation completed without errors (not counting any OBO-specific errors).")
        else:
            print("Operation encountered errors. See logs for details.")

    except Exception as e:
        print(f"Encountered unresolvable error: {type(e)} - {e} ({e.args})")
        print("Removing lock due to error...")
        if s3_test:
            if not kg_obo.upload.mock_set_lock(bucket,lock_file_remote_path,unlock=True):
                print("Could not mock setting lock file.")
        else:
            if not kg_obo.upload.set_lock(bucket,lock_file_remote_path,unlock=True):
                print("Could not remove lock file due to yet another error.")
            else:
                print("Lock removed.")
        sys.exit(-1)

    print("Generating reports...")
    try:
        from kg_obo.stats import get_all_stats
        
        if get_all_stats(skip, get_only, bucket, save_local):
            print("Reports generated without errors. See stats directory.")
            if kg_obo.upload.upload_reports(bucket):
                print(f"Uploaded reports to {bucket}.")
            else:
                print(f"Could not upload reports to {bucket}.")
        else:
            print("Stats reports could not be generated.")
    except Exception as e:
        print(f"Encountered unresolvable error while generating stats: {type(e)} - {e}")

if __name__ == '__main__':
  run()
