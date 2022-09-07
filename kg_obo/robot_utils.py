#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
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


def convert_owl(robot_path: str, input_owl: str, output: str, robot_env: dict) -> bool:
    """
    This method runs a convert ROBOT command on a single OBO.
    :param robot_path: Path to ROBOT files
    :param input_owl: Ontology file to be relaxed
    :param output: Ontology file to be created (needs valid ROBOT suffix)
    :param robot_env: dict of environment variables, including ROBOT_JAVA_ARGS
    :return: True if completed without errors, False if errors
    """

    success = False

    print(f"Converting {input_owl} to {output}...")

    robot_command = sh.Command(robot_path)

    try:
        robot_command('convert',
            '--input', input_owl,
            '--format', 'json',
            '--output', output,
            _env=robot_env,
        )
        print("Complete.")
        success = True
    except sh.ErrorReturnCode_1 as e: # If ROBOT runs but returns an error
        print(f"ROBOT encountered an error: {e}")
        success = False

    return success


def merge_and_convert_owl(robot_path: str, input_owl: str, output: str, robot_env: dict) -> bool:
    """
    This method runs a merge and convert ROBOT command on a single OBO.
    Has a three-hour timeout limit - process is killed if it takes this long.
    :param robot_path: Path to ROBOT files
    :param input_owl: Ontology file to be relaxed
    :param output: Ontology file to be created (needs valid ROBOT suffix)
    :param robot_env: dict of environment variables, including ROBOT_JAVA_ARGS
    :return: True if completed without errors, False if errors
    """

    success = False

    print(f"Merging and converting {input_owl} to {output}...")

    robot_command = sh.Command(robot_path)

    try:
        robot_command('merge',
            '--input', input_owl,
            'convert', 
            '--output', output,
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
    :param output_log: Location of log file to be created
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

def examine_owl_names(robot_path: str, 
                        input_owl: str,
                        output_dir: str,
                        curie_converter: Converter, 
                        iri_converter: Converter, 
                        robot_env: dict) -> bool:
    """
    This method attempts to retrieve all entity identifiers for a single OBO in OWL.

    Reports all identifiers of expected and unexpected format,
    and finds more appropriate prefixes if possible.
    Does not rewrite IRIs.
    :param robot_path: Path to ROBOT files
    :param input_owl: Ontology file to be normalized
    :param output_dir: string of directory, location of unexpected id 
    and update map file to be created
    :param curie_converter: a curies Converter object with defined prefix maps,
    from CURIE prefix to IRI prefix
    :param iri_converter: a curies Converter object with defined prefix maps,
    from IRI prefix to CURIE prefix
    :param robot_env: dict of environment variables, including ROBOT_JAVA_ARGS
    :return: True if completed without errors, False if errors
    """

    # TODO: get other things KGX will use as nodes, beyond entity IRIs

    success = False

    id_list = []
    mal_id_list = []
    update_ids: Dict[str, str] = {}

    print(f"Retrieving entity names in {input_owl}...")

    robot_command = sh.Command(robot_path)
    tempfile_name = input_owl + ".ids.csv"
    mal_id_file_name = os.path.join(output_dir, "unexpected_ids.tsv")
    update_mapfile_name = os.path.join(output_dir, "update_id_maps.tsv")

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
        # Also checks if IDs with OBO prefixes should be something else.
        try:
            for identifier in id_list:
                # See if there's an OBO prefix
                if (identifier.split(":"))[0].upper() == "OBO":
                    mal_id_list.append(identifier)
                    new_id = ((identifier[4:]).replace("_",":")).upper()
                    split_new_id = new_id.split("/")
                    if split_new_id[0].endswith("OWL"):
                        new_id = split_new_id[1]
                    update_ids[identifier] = new_id
                    continue
                try: 
                    assert curie_converter.expand(identifier)
                except AssertionError:
                    mal_id_list.append(identifier)
                    new_id = iri_converter.compress(identifier)
                    if new_id:
                        if new_id[0].islower(): # Need to capitalize
                            split_id = new_id.split(":")
                            new_id = f"{split_id[0].upper()}:{split_id[1]}"
                        update_ids[identifier] = new_id
        except IndexError:
            mal_id_list.append(identifier)

        mal_id_list_len = len(mal_id_list)
        if mal_id_list_len > 0:
            print(f"Found {mal_id_list_len} unexpected identifiers.")
            with open(mal_id_file_name, 'w') as idfile:
                idfile.write("ID\n")
                for identifier in mal_id_list:
                    idfile.write(f"{identifier}\n")
        else:
            print(f"All identifiers in {input_owl} are as expected.")

        update_id_len = len(update_ids)
        if update_id_len > 0:
            print(f"Will normalize {update_id_len} identifiers.")
            with open(update_mapfile_name, 'w') as mapfile:
                mapfile.write("Old ID\tNew ID\n")
                for identifier in update_ids:
                    mapfile.write(f"{identifier}\t{update_ids[identifier]}\n")
                print(f"Wrote IRI maps to {update_mapfile_name}.")
        else:
            print(f"No identifiers in {input_owl} will be normalized.")

    return success
