#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sh # type: ignore
from sh import chmod # type: ignore

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
    Yields all metrics as string and as a log file.

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