# KG-OBO

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=alert_status)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Knowledge-Graph-Hub_kg-obo&metric=coverage)](https://sonarcloud.io/dashboard?id=Knowledge-Graph-Hub_kg-obo)

## What is it?

**KG-OBO** is a package to transform all [OBO Foundry ontologies](http://obofoundry.org/) into [KGX TSV format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md), collect graph statistics on each ontology, and make the new graph nodes/edges available on [KG-Hub](https://knowledge-graph-hub.github.io/).

Documentation is [here](https://knowledge-graph-hub.github.io/kg-obo/getting_started.html).
See also the guides in the `guides` directory for specific use case examples.

OBO ontologies transformed into graph nodes and edges are available [here](https://knowledge-graph-hub.github.io/kg_obo/).
You may also see the full collection of graphs [here](https://kg-hub.berkeleybop.io/kg-obo/).

## Why?

Knowledge graphs, or KGs, are powerful tools for modeling and learning from the complex relationships being constantly discovered among biological and biomedical phenomena. Though it can be useful to assemble a set of interactions alone (e.g., between proteins, genes, and even diseases or their symptoms), a complete understanding of these associations may be difficult to acquire without comprehensive domain knowledge. 

This is where ontologies can help. Each ontology defines the relationships between concepts, often in hierarchies. If you need to know whether [salicylsulfuric acid](https://www.ontobee.org/ontology/CHEBI?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FCHEBI_134899) and [fenpicoxamid](https://www.ontobee.org/ontology/CHEBI?iri=http://purl.obolibrary.org/obo/CHEBI_136340) have anything in common (they're both esters, at least), the [CHEBI](https://obofoundry.org/ontology/chebi.html) ontology can help. If you're trying to model the relationships between the cephalopod [*Enoploteuthis leptura*](https://www.ontobee.org/ontology/CEPH?iri=http://purl.obolibrary.org/obo/NCBITaxon_283049) and other species, there's [an ontology](https://obofoundry.org/ontology/ceph.html) for that too. 

Ontologies are carefully designed to define specific relationships and their internal formats reflect this purpose. These formats (often OWL or OBO) are not naturally compatible with knowlege graph assembly. Their classes require translation into nodes and their relationships must be translated into edges, all with a single, consistent format retaining as much of the original ontology's value as possible. It's also preferable to keep track of which version of each ontology is to be used in a KG, for the sake of reproducibility.

KG-OBO takes care of this for you.

### How can KG-OBO graphs be used in a new project?

Individual versions of OBO ontology graphs [may be downloaded directly from KG-Hub](https://kg-hub.berkeleybop.io/kg-obo/). Each directory has the same identifier as on OBO Foundry. Inside a directory, each version has its own subdirectory, and each subdirectory contains:

* {name}_kgx_tsv.tar.gz - a compressed file containing the graph nodes and edges, both in KGX TSV format.
* {name}_kgx.json - the graph nodes and edges in [OBO JSON format](https://github.com/geneontology/obographs).
* tsv_transform.log - a log of the transformation process for TSV format.
* json_transform.log  - a log of the transformation process for OBO JSON format.

For example, if you need to retrieve the 2021-12-12 release of the Zebrafish Phenotype ontology, you may do the following on a Linux command line:

```
$ wget https://kg-hub.berkeleybop.io/kg-obo/zp/2021-12-12/zp_kgx_tsv.tar.gz
$ tar xvzf zp_kgx_tsv.tar.gz
```

The nodes and edges will be in `zp_kgx_tsv_nodes.tsv` and `zp_kgx_tsv_edges.tsv`, respectively.

Ontologies from KG-OBO are great foundations for a [new KG-Hub project based on our template](https://github.com/Knowledge-Graph-Hub/kg-dtm-template), too! They may be loaded into KG-Hub graphs with minimal further effort.

The [KG-IDG](https://github.com/Knowledge-Graph-Hub/kg-idg) project uses KG-OBO graphs. 

## How does it work?

As a user, you likely will not need to run KG-OBO yourself and may find its products more useful.

You are welcome to borrow code (under [license](https://github.com/Knowledge-Graph-Hub/knowledge-graph-hub-support/blob/main/LICENSE), of course) as inspiration for your own graph-driven project.

The code itself is designed to be run on a regular basis - at least a few times a month - through a Jenkins build process. 

This allows automatic completion of:
* Searching for and downloading new versions of each OBO Foundry ontology as they become available.
* Transforming ontologies from OBO format to KGX node and edge lists.
* Tracking each version of each ontology, including chages in size and graph metrics between versions.
* Storing transformed ontology graphs on KG-Hub.

KG-OBO uses [ROBOT](http://robot.obolibrary.org/) - this is installed if it is not already present.

### How can I try it out? ###

KG-OBO assumes you are working in a Linux environment with at least Python 3.8.

Install it by cloning this respository:
```
$ git clone https://github.com/Knowledge-Graph-Hub/kg-obo.git
$ cd kg-obo
$ python -m pip install .
```

Then run the following to test it out:
```
$ python run.py --get_only bfo --s3_test --bucket test --save_local
```
This will tell KG-OBO to retrieve the [Basic Formal Ontology](https://obofoundry.org/ontology/bfo) and transform it, skipping uploading steps.

With the `--save_local` option, the transformed output will be found in `kg-obo/data/bfo/` (otherwise, it is deleted). Expect to see six files in total, one of which, bfo_kgx_tsv.tar.gz, will contain the nodes and edges of this ontology.

## Where should issues be reported?
[Please let us know about any issues with KG-OBO transforms on GitHub.](https://github.com/Knowledge-Graph-Hub/kg-obo/issues/new/choose)

You can also visit the [KG-Hub support spot](https://github.com/Knowledge-Graph-Hub/knowledge-graph-hub-support) to discuss any general KG-Hub issues, feature requests, or help with assembling your own knowledge graph.
