#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sh # type: ignore
from sh import chmod # type: ignore

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

    # Make sure it's executable
    chmod("+x","robot")

    # Declare environment variables
    env = dict(os.environ)
    # (JDK compatibility issue: https://stackoverflow.com/questions/49962437/unrecognized-vm-option-useparnewgc-error-could-not-create-the-java-virtual)
    # env['ROBOT_JAVA_ARGS'] = '-Xmx8g -XX:+UseConcMarkSweepGC' # for JDK 9 and older
    env['ROBOT_JAVA_ARGS'] = '-Xmx12g -XX:+UseG1GC'  # For JDK 10 and over
    env['PATH'] = os.environ['PATH']
    env['PATH'] += os.pathsep + robot_path

    try:
        robot_command = sh.Command(robot_path)
    except sh.CommandNotFound: # If for whatever reason ROBOT isn't available
        robot_command = None

    return [robot_command, env]


def relax_owl(robot_path: str, input_owl: str, output_owl: str) -> None:
    """
    This method runs the ROBOT relax command on a single OBO.
    Has a three-hour timeout limit - process is killed if it takes this long.
    :param robot_path: Path to ROBOT files
    :param input_owl: Ontology file to be relaxed
    :param output_owl: Ontology file to be created (needs valid ROBOT suffix)
    :return: None
    """

    robot_command = sh.Command(robot_path)

    robot_command('relax',
            '--input', input_owl, 
            '--output', output_owl,
            _timeout=10800 
    )

def merge_and_convert_owl(robot_path: str, input_owl: str, output_owl: str) -> None:
    """
    This method runs a merge and convert ROBOT command on a single OBO.
    Has a three-hour timeout limit - process is killed if it takes this long.
    :param robot_path: Path to ROBOT files
    :param input_owl: Ontology file to be relaxed
    :param output_owl: Ontology file to be created (needs valid ROBOT suffix)
    :return: None
    """

    robot_command = sh.Command(robot_path)

    robot_command('merge',
            '--input', input_owl,
            'convert', 
            '--output', output_owl,
            _timeout=10800 
    )