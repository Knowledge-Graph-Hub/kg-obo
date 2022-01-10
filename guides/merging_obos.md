# Merging OBOs

Why merge OBOs into a single graph? A snapshot of combined hierarchical relationships may be a necessary component of a knowledge graph, or it may simply be the most convenient (and more importantly, reproducible) way to share sets of related axioms. For example, projects involving both zebrafish and Xenopus as model organisms may require both the [Zebrafish anatomy and development ontology](https://obofoundry.org/ontology/zfa.html) and the [Xenopus anatomy ontology](https://obofoundry.org/ontology/xao.html). Or, you may require the conceptual relationships provided by the [Biological Imaging Methods Ontology](https://obofoundry.org/ontology/fbbi.html) and the [Basic Formal Ontology](https://obofoundry.org/ontology/bfo.html).

Ontologies from the [OBO Foundry](http://obofoundry.org/) may be merged in two different ways: through a pipeline for the [Ontology Development Kit](https://github.com/INCATools/ontology-development-kit) or directly through [KGX](https://github.com/biolink/kgx). The former method offers the benefit of providing all necessary dependencies in a premade Docker image and may be most appropriate for ontology developers (e.g., if you are actively working on an OBO ontology but wish to use it in a graph along with other OBOs). The strategy relies upon selecting a set of OBOs, merging them, then using KG-OBO to transform to nodes/edges. The KGX method offers more direct control over the desired contents of the output, as its inputs are defined by a single configuration file. Unlike ODK, this approach works with individual sets of transformed OBOs, then merges the node and edgelists. While this method is more straightforward, its tools are blissfully unaware of ideosyncracies such as equivalent classes

With both methods, the final product will be nodes and edges corresponding to the contents of the input ontologies.

## Ontology Development Kit (ODK)

More examples for getting started with ODK, including Windows-specific commands, [may be found here.](https://github.com/INCATools/ontology-development-kit/blob/master/docs/CreatingRepo.md) You may encounter difficulties in working with larger ontologies such as PR or NCBITaxon, and if so, [see the tips here.](https://github.com/INCATools/ontology-development-kit/blob/master/docs/DealWithLargeOntologies.md)


The ODK Docker container may be retrieved as follows:

```
docker pull obolibrary/odkfull
```

The full image is a > 1 Gb download and > 2 Gb on disk.

Get the wrapper script for the ODK Docker container:

```
wget https://raw.githubusercontent.com/INCATools/ontology-development-kit/master/seed-via-docker.sh
chmod u+x seed-via-docker.sh
```

Edit the project config file (here, it's `project.yaml`) so that it defines your ontologies, each preceded by `id` under the heading `products`. Changing the `id` on the first line to and the `repo` name to your choice of name are good ideas as well. You'll also want to change the `github_org` value to your own GitHub username if you're planning on creating a new repository, but here we are primarily using the newly created files as graph precursors. (Or, in the following command, append `-u username`, changing username to your GitHub username.) 

Use the script to retrive your OBOs:
```
./seed-via-docker.sh -C project.yaml
```

A `target` directory will be created in the current working directory.

**TODO: complete this section.**

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