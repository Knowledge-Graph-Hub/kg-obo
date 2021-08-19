# obo2kghub

A package to transform all [OBO ontologies](http://obofoundry.org/) into [KGX TSV format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md), and put the transformed graph in [KGhub](http://kg-hub.berkeleybop.io/index.html)

Requires installation of [ROBOT](http://robot.obolibrary.org/) to transform OWL to JSON.
To install ROBOT:
1. Run `curl https://github.com/ontodev/robot/releases/download/v1.8.1/robot.jar > robot.jar`
2. Run `curl https://raw.githubusercontent.com/ontodev/robot/master/bin/robot > robot` in the same directory.
3. Move both to your system PATH, e.g., as follows: `sudo mv robot* /usr/local/bin/`
4. Ensure they are executable: `sudo chmod +x /usr/local/bin/robot`
