# obo2kghub

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=alert_status)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=coverage)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)

A package to transform all [OBO ontologies](http://obofoundry.org/) into [KGX TSV format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md), and put the transformed graph in [KGhub](http://kg-hub.berkeleybop.io/index.html)

Requires installation of [ROBOT](http://robot.obolibrary.org/) to transform OWL to JSON.
To install ROBOT:
1. Download `robot.jar` from https://github.com/ontodev/robot/releases/latest
2. Run `curl https://raw.githubusercontent.com/ontodev/robot/master/bin/robot > robot` in the same directory.
3. Move both to your system PATH, e.g., as follows: `sudo mv robot* /usr/local/bin/`
4. Ensure they are executable: `sudo chmod +x /usr/local/bin/robot`
