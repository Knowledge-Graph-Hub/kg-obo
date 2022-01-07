# Merging OBOs

Why merge OBOs into a single graph? A snapshot of combined hierarchical relationships may be a necessary component of a knowledge graph, or it may simply be the most convenient (and more importantly, reproducible) way to share sets of related axioms. For example, projects involving both zebrafish and Xenopus as model organisms may require both the [Zebrafish anatomy and development ontology](https://obofoundry.org/ontology/zfa.html) and the [Xenopus anatomy ontology](https://obofoundry.org/ontology/xao.html).

Ontologies from the [OBO Foundry](http://obofoundry.org/) may be merged in two different ways: through a pipeline for the [Ontology Development Kit](https://github.com/INCATools/ontology-development-kit) or directly through [KGX](https://github.com/biolink/kgx). The former method offers the benefit of providing all necessary dependencies in a premade Docker image. The latter method offers more direct control over the desired contents of the output.

With both methods, the final product will be nodes and edges corresponding to the contents of the input ontologies.

## Ontology Development Kit (ODK)

## KGX

Install KGX:

```
pip install kgx
```

Retreive ontologies from KG-OBO, replacing each URL here with one to the .tar.gz for the desired ontology and version:

```
wget -i - https://kg-hub.berkeleybop.io/kg-obo/fbbi/2020-11-06/fbbi_kgx_tsv.tar.gz https://kg-hub.berkeleybop.io/kg-obo/bfo/2019-08-26/bfo_kgx_tsv.tar.gz
```

Once downloads are complete, press CTRL+D to finish.

Decompress all freshly downloaded files:
```
cat *.tar.gz | tar zxvf - -i
```

Edit the merge config file (here, it's `merge-template.yaml`) so that it defines your ontologies.

Each entry should look like:
```
    obo1:
      name: "OBO One"
      input:
        format: tsv
        filename:
          - obo1_nodes.tsv
          - obo1_edges.tsv
```

Finally, use KGX to merge:
```
kgx merge --merge-config merge-template.yaml
```

The merged node and edgelists will be written to the current directory.