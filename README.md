# kg_obo

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=alert_status)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=coverage)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)

A package to transform all [OBO ontologies](http://obofoundry.org/) into [KGX TSV format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md), and put the transformed graph in [KGhub](http://kg-hub.berkeleybop.io/index.html)

### Installation:
```
git clone https://github.com/Knowledge-Graph-Hub/kg-obo.git
cd kg-obo
python -m venv venv # optional
pip install .
```

### Usage:
```
python run.py
```

### Details:
`run.py` iterates through ontologies found in [this YAML file](https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml), checks whether an existing transform for each ontologies exists on the target s3 bucket directory using the `tracking.yaml` file (see below), and if not transforms the ontology from OWL to KGX TSV, and puts the KGX nodes/edges TSV files up on the bucket at:
`s3_bucket/[target directory]/[ontology name]/[version]/`

A file called `tracking.yaml` is used to keep track of what transforms exist for a given ontology. This remote file is checked to decide whether a transform is necessary, and is also updated remotely after a given transform completes. 

####  `tracking.yaml` file: OBO to Node/Edge Transform Tracking
The OBO to Node/Edge Transform Tracking (tracking.yaml) file is used to keep track of current and previous version of transformed ontologies.

Each entry, named by its OBO ID, must contain the following:
 
`'current_iri'`: the most recent version of the ontology, expressed as a full IRI, e.g.,          
          http://purl.obolibrary.org/obo/bfo/2019-08-26/bfo.owl
 
`'current_version'`: the most recent version of the ontology, expressed as a version string, e.g.,
          2019-08-26

The following two items may not exist if only one version is available:

`'archive_iris'`: previous versions of the ontology, expressed in the format of 'current_iri'.
 
`'archive_versions'`: previous versions of the ontology, expressed in the format of 'current_version'.
