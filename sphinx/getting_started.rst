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

`run.py` iterates through ontologies found in [this YAML file](https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/mas\
ter/registry/ontologies.yml), checks whether an existing transform for each ontologies exists on the target s3 bucket directory usin\
g the `tracking.yaml` file (see below), and if not transforms the ontology from OWL to KGX TSV, and puts the KGX nodes/edges TSV fil\
es up on the bucket at:
`s3_bucket/[target directory]/[ontology name]/[version]/`

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
