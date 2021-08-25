#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Transform all available OBO Foundry ontologies from OBO format
to KGX TSV, with intermediate JSON.
"""
from kg_obo.transform import run_transform

run_transform(skip_list=[''])
