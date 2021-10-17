#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from sh import robot

# Note that sh module can take environment variables, see
# https://amoffat.github.io/sh/sections/special_arguments.html#env

def initialize_robot(path: str) -> list:
    """
    This initializes ROBOT with necessary configuration.
    :param path: Path to ROBOT files.
    :return: A list consisting of robot shell script name and environment variables.
    """
    # Declare variables
    robot_file = path
    if os.path.basename(path) != "robot":
        raise ValueError("Path does not appear to include ROBOT.")

    # Declare environment variables
    env = dict(os.environ)
    # (JDK compatibility issue: https://stackoverflow.com/questions/49962437/unrecognized-vm-option-useparnewgc-error-could-not-create-the-java-virtual)
    # env['ROBOT_JAVA_ARGS'] = '-Xmx8g -XX:+UseConcMarkSweepGC' # for JDK 9 and older
    env['ROBOT_JAVA_ARGS'] = '-Xmx12g -XX:+UseG1GC'  # For JDK 10 and over
    env['PATH'] = os.environ['PATH']
    env['PATH'] += os.pathsep + path

    return [robot_file, env]


def relax_owl(robot_path: str, input_owl: str, output_owl: str) -> None:
    """
    This method runs the ROBOT relax command on a single OBO.
    Has a three-hour timeout limit - process is killed if it takes this long.
    :param robot_path: Path to ROBOT files
    :param input_owl: Ontology file to be relaxed
    :param output_owl: Ontology file to be created (needs valid ROBOT suffix)
    :return: None
    """

    robot_file, env = initialize_robot(robot_path)

    robot('relax',
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

    robot_file, env = initialize_robot(robot_path)

    robot('merge',
            '--input', input_owl,
            'convert', 
            '--output', output_owl,
            _timeout=10800 
    )