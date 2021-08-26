# kg_obo

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=alert_status)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=coverage)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)

A package to transform all [OBO ontologies](http://obofoundry.org/) into [KGX TSV format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md), and put the transformed graph in [KGhub](http://kg-hub.berkeleybop.io/index.html)

## OBO to Node/Edge Transform Tracking (tracking.yaml)
Each entry, separated by "-", must contain the following:
 
'name': the name of an ontology, following OBO ID conventions, e.g.,
          bfo
 
'current_iri': the most recent version of the ontology, expressed as a full IRI, e.g.,          
          http://purl.obolibrary.org/obo/bfo/2019-08-26/bfo.owl
 
'current_version': the most recent version of the ontology, expressed as a version string, e.g.,
          2019-08-26
 
'archive_iris': previous versions of the ontology, expressed in the format of 'current_iri'.
          May not exist if only one version is available.
 
'archive_versions': previous versions of the ontology, expressed in the format of 'current_version'.
          May not exist if only one version is available.
