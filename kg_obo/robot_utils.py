#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import \
    subprocess  # Source: https://docs.python.org/2/library/subprocess.html#popen-constructor

# H/T Harshad Hegde - this code is lifted from kg-microbe:
# https://github.com/Knowledge-Graph-Hub/kg-microbe


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
    This method runs the ROBOT relax command using the subprocess library
    :param robot_path: Path to ROBOT files
    :param ont: Ontology file to be relaxed
    :return: None
    """

    robot_file, env = initialize_robot(robot_path)

    call = ['bash', robot_path, 'relax',
            '--input', input_owl, 
            '--output', output_owl, 
            ]

    subprocess.call(call, env=env)


def merge_and_convert_owl(path: str, ont: str) -> str:
    """
    This method runs a merge and convert ROBOT command using the subprocess library
    :param path: Path to ROBOT files
    :param ont: Ontology
    :return: None
    """

    robot_file, env = initialize_robot(path)
    input_owl = os.path.join(path, ont.lower() + '.owl')
    output_json = os.path.join(path, ont.lower() + '.json')
    # if not os.path.isfile(output_json):
    #     # Setup the arguments for ROBOT through subprocess
    #     call = ['bash', robot_file, 'convert', \
    #             '--input', input_owl, \
    #             '--output', output_json, \
    #             '-f', 'json']

    #     subprocess.call(call, env=env)

    return output_json