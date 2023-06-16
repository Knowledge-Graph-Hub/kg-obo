import os
from shutil import rmtree
import urllib.request

def robot_setup():
    """
    Downloads ROBOT jar and run script.
    """

    robotjar_paths = {"local":"robot.jar",
                    "remote":"https://github.com/ontodev/robot/releases/download/v1.8.3/robot.jar"}
    robot_paths = {"local":"robot",
                    "remote":"https://raw.githubusercontent.com/ontodev/robot/master/bin/robot"}
    # Check if they already exist
    for filepath in [robotjar_paths, robot_paths]:
        localfile = filepath["local"]
        remotefile = filepath["remote"]
        if os.path.isfile(localfile):
            print(f"Found file: {localfile}")
        else:
            print(f"Did not find {localfile}. Downloading from {remotefile}...")
            urllib.request.urlretrieve(remotefile, localfile)

if __name__ == '__main__':
    robot_setup()
