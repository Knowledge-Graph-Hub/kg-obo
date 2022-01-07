# Merging OBOs

Why merge OBOs into a single graph? A snapshot of combined hierarchical relationships may be a necessary component of a knowledge graph, or it may simply be the most convenient (and more importantly, reproducible) way to share sets of related axioms. For example, projects involving both zebrafish and Xenopus as model organisms may require both the [Zebrafish anatomy and development ontology](https://obofoundry.org/ontology/zfa.html) and the [Xenopus anatomy ontology](https://obofoundry.org/ontology/xao.html).

Ontologies from the [OBO Foundry](http://obofoundry.org/) may be merged in two different ways: through a pipeline for the [Ontology Development Kit](https://github.com/INCATools/ontology-development-kit) or directly through [KGX](https://github.com/biolink/kgx). The former method offers the benefit of providing all necessary dependencies in a premade Docker image. The latter method offers more direct control over the desired contents of the output.

With both methods, the final product will be nodes and edges corresponding to the contents of the input ontologies.

## Ontology Development Kit (ODK)

## KGX