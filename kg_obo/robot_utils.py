#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from typing import Dict

import sh  # type: ignore
from curies import Converter  # type: ignore
from sh import chmod  # type: ignore

from post_setup.post_setup import robot_setup

# Note that sh module can take environment variables, see
# https://amoffat.github.io/sh/sections/special_arguments.html#env

def initialize_robot(robot_path: str) -> list:
    """
    This initializes ROBOT with necessary configuration.
    During install, ROBOT is downloaded to the same directory as kg-obo,
    and the path variable used here is only necessary if it varies from
    the kg-obo location.
    :param path: Path to ROBOT files.
    :return: A list consisting an instance of Command and dict of all environment variables.
    """

    # We may have made it this far without installing ROBOT, so do that now if needed
    if not os.path.exists(robot_path):
        robot_setup()
    
    # Make sure it's executable
    chmod("+x","robot")

    # Declare environment variables
    env = os.environ.copy()
    # (JDK compatibility issue: https://stackoverflow.com/questions/49962437/unrecognized-vm-option-useparnewgc-error-could-not-create-the-java-virtual)
    # env['ROBOT_JAVA_ARGS'] = '-Xmx8g -XX:+UseConcMarkSweepGC' # for JDK 9 and older
    env['ROBOT_JAVA_ARGS'] = '-Xmx12g -XX:+UseG1GC'  # For JDK 10 and over

    try:
        robot_command = sh.Command(robot_path)
    except sh.CommandNotFound: # If for whatever reason ROBOT isn't available
        robot_command = None

    return [robot_command, env]


def relax_owl(robot_path: str, input_owl: str, output_owl: str, robot_env: dict) -> bool:
    """
    This method runs the ROBOT relax command on a single OBO.
    Has a three-hour timeout limit - process is killed if it takes this long.
    :param robot_path: Path to ROBOT files
    :param input_owl: Ontology file to be relaxed
    :param output_owl: Ontology file to be created (needs valid ROBOT suffix)
    :param robot_env: dict of environment variables, including ROBOT_JAVA_ARGS
    :return: True if completed without errors, False if errors
    """

    success = False

    print(f"Relaxing {input_owl} to {output_owl}...")

    robot_command = sh.Command(robot_path)

    try:
        robot_command('relax',
            '--input', input_owl, 
            '--output', output_owl,
            '--vvv',
            _env=robot_env,
            _timeout=10800 
        )
        print("Complete.")
        success = True
    except sh.ErrorReturnCode_1 as e: # If ROBOT runs but returns an error
        print(f"ROBOT encountered an error: {e}")
        success = False

    return success


def merge_and_convert_owl(robot_path: str, input_owl: str, output_owl: str, robot_env: dict) -> bool:
    """
    This method runs a merge and convert ROBOT command on a single OBO.
    Has a three-hour timeout limit - process is killed if it takes this long.
    :param robot_path: Path to ROBOT files
    :param input_owl: Ontology file to be relaxed
    :param output_owl: Ontology file to be created (needs valid ROBOT suffix)
    :param robot_env: dict of environment variables, including ROBOT_JAVA_ARGS
    :return: True if completed without errors, False if errors
    """

    success = False

    print(f"Merging and converting {input_owl} to {output_owl}...")

    robot_command = sh.Command(robot_path)

    try:
        robot_command('merge',
            '--input', input_owl,
            'convert', 
            '--output', output_owl,
            '--vvv',
            _env=robot_env,
            _timeout=10800 
        )
        print("Complete.")
        success = True
    except sh.ErrorReturnCode_1 as e: # If ROBOT runs but returns an error
        print(f"ROBOT encountered an error: {e}")
        success = False

    return success

def measure_owl(robot_path: str, input_owl: str, output_log: str, robot_env: dict) -> bool:
    """
    This method runs the ROBOT measure command on a single OBO in OWL.

    :param robot_path: Path to ROBOT files
    :param input_owl: Ontology file to be validated
    :param output_owl: Location of log file to be created
    :param robot_env: dict of environment variables, including ROBOT_JAVA_ARGS
    :return: True if completed without errors, False if errors
    """
    success = False

    print(f"Obtaining metrics for {input_owl}...")

    robot_command = sh.Command(robot_path)

    profile = 'Full'

    try:
        robot_command('measure',
            '--input', input_owl,
            '--format', 'tsv',
            '--metrics', 'all',
            '--output', output_log,
            _env=robot_env,
        )
        print(f"Complete. See log in {output_log}")
        success = True
    except sh.ErrorReturnCode_1 as e: # If ROBOT runs but returns an error
        print(f"ROBOT encountered an error: {e}")
        success = False

    return success

def normalize_owl_names(robot_path: str, input_owl: str, converter: Converter, robot_env: dict) -> bool:
    """
    This method attempts to normalize all entity identifiers a single OBO in OWL.

    Reports all identifiers of unexpected format,
    and attempts to rename if possible.
    :param robot_path: Path to ROBOT files
    :param input_owl: Ontology file to be normalized
    :param coverter: a curies Converter object with defined prefix maps
    :param robot_env: dict of environment variables, including ROBOT_JAVA_ARGS
    :return: True if completed without errors, False if errors
    """

    # TODO: get other things KGX will use as nodes, beyond entity IRIs
    # TODO: ensure all CURIEs are capitalized

    success = False

    id_list = []
    mal_id_list = []
    update_ids: Dict[str, str] = {}

    print(f"Retrieving entity names in {input_owl}...")

    robot_command = sh.Command(robot_path)
    tempfile_name = input_owl + ".ids.csv"
    mapping_file_name = input_owl + ".maps.csv"

    try:
        robot_command('export',
            '--input', input_owl,
            '--header', 'ID',
            '--export', tempfile_name,
            _env=robot_env,
        )
        print(f"Exported IDs to {tempfile_name}.")
        success = True
    except sh.ErrorReturnCode_1 as e: # If ROBOT runs but returns an error
        print(f"ROBOT encountered an error: {e}")
        success = False

    if success:
        with open(tempfile_name, 'r') as idfile:
            idfile.readline()
            for line in idfile:
                id_list.append(line.rstrip())

        # For each id, assume it is a CURIE and try to convert to IRI.
        # If that doesn't work, it might be an IRI - try to
        # convert it to a CURIE. If that works, we need to update it.
        for identifier in id_list:
            try: 
                assert converter.expand(identifier)
            except AssertionError:
                mal_id_list.append(identifier)
                new_id = converter.compress(identifier)
                if new_id:
                    if new_id[0].islower(): # Need to capitalize
                        split_id = new_id.split(":")
                        new_id = f"{split_id[0].upper()}:{split_id[1]}"
                    update_ids[identifier] = new_id

        
        
        mal_id_list_len = len(mal_id_list)
        if mal_id_list_len > 0:
            print(f"Found {mal_id_list_len} unexpected identifiers:")
            for identifier in mal_id_list:
                print(identifier)
        else:
            print(f"All identifiers in {input_owl} are as expected.")

        update_id_len = len(update_ids)
        if update_id_len > 0:
            print(f"Will normalize {update_id_len} identifiers:")
            with open(mapping_file_name, 'w') as mapfile:
                for identifier in update_ids:
                    print(f"{identifier} -> {update_ids[identifier]}")
                    mapfile.write(f"{identifier},{update_ids[identifier]}")
        else:
            print(f"No identifiers in {input_owl} will be normalized.")

        if update_id_len > 0:
            temp_outfile = input_owl + ".tmp.owl"
            try:
                robot_command('rename',
                    '--input', input_owl,
                    '--mappings', mapping_file_name,
                    '--output', temp_outfile,
                    _env=robot_env,
                )

                shutil.move(temp_outfile, input_owl)

                success = True
            except sh.ErrorReturnCode_1 as e: # If ROBOT runs but returns an error
                print(f"ROBOT encountered an error: {e}")
                success = False

    return success
