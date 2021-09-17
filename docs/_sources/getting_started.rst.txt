Quick Start
-----------

.. code:: sh

       git clone https://github.com/Knowledge-Graph-Hub/kg-obo
       cd kg-obo
       python3 -m venv venv && source venv/bin/activate # optional
       pip install .
       python run.py --bucket [your s3 bucket]

Overview
________

`run.py` iterates through ontologies found in `this YAML file <https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml>`__, checks whether an existing transform for each ontologies exists on the target s3 bucket directory usin\
g the `tracking.yaml` file, and if not transforms the ontology from OWL to KGX TSV, and puts the KGX nodes/edges TSV fil\
es up on the bucket at:
`s3_bucket/[target directory]/[ontology name]/[version]/`

`tracking.yaml <https://kg-hub.berkeleybop.io/kg-obo/tracking.yaml>`__ file: OBO to Node/Edge Transform Tracking
The OBO to Node/Edge Transform Tracking (tracking.yaml) file is used to keep track of current and previous version of transformed ontologies.

Each entry, named by its OBO ID, must contain the following:

`'current_iri'`: the most recent version of the ontology, expressed as a full IRI, e.g.,
          http://purl.obolibrary.org/obo/bfo/2019-08-26/bfo.owl

`'current_version'`: the most recent version of the ontology, expressed as a version string, e.g.,
          2019-08-26

The following two items may not exist if only one version is available:

`'archive_iris'`: previous versions of the ontology, expressed in the format of 'current_iri'.

`'archive_versions'`: previous versions of the ontology, expressed in the format of 'current_version'.

Download ontologies in KGX format
---------------------------------

OBO ontologies transformed into are available here:

`https://kg-hub.berkeleybop.io/kg-obo/`

See `here <https://github.com/biolink/kgx/blob/master/specification/kgx-format.md>`__
for a description of the KGX TSV format

Installation
~~~~~~~~~~~~

.. code:: sh

       git clone https://github.com/Knowledge-Graph-Hub/kg-obo
       cd kg-obo
       python3 -m venv venv && source venv/bin/activate # optional
       pip install .

Running the pipeline
~~~~~~~~~~~~~~~~~~~~

.. code:: sh

       python3 run.py --bucket [your s3 bucket]

How to Contribute
-----------------

Download and use the code
~~~~~~~~~~~~~~~~~~~~~~~~
Download and use the code, and any issues and questions
`here <https://github.com/Knowledge-Graph-Hub/kg-obo/issues/new/choose>`__.

Contributors
------------

-  `Harry Caufield <https://github.com/caufieldjh>`__
-  `Justin Reese <https://github.com/justaddcoffee>`__
-  `Harshad Hegde <https://github.com/hrshdhgd>`__


Acknowledgements
----------------

We gratefully acknowledge the OBO community and thank all participants for
making their data available.
