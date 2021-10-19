import os
from unittest import TestCase, mock
from unittest.mock import Mock

from kg_obo.robot_utils import relax_owl, merge_and_convert_owl

class TestRobotUtils(TestCase):

    def setUp(self) -> None:
        self.robot_path = os.path.join(os.getcwd(),"robot")
        self.input_owl = 'tests/resources/download_ontology/bfo.owl'
        self.output_owl = 'tests/resources/download_ontology/bfo_processed.owl'

    def test_relax_owl(self):
        relax_owl(self.robot_path, self.input_owl, self.output_owl)

    def test_merge_and_convert_owl(self):
        relax_owl(self.robot_path, self.input_owl, self.output_owl)