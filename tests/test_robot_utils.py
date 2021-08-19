import os.path
from unittest import TestCase, mock

from kg_obo.robot_utils import convert_owl_to_json, initialize_robot


class TestRobotUtils(TestCase):

    def setUp(self) -> None:
        pass

    @mock.patch('subprocess.call')
    def test_convert_owl_to_json(self, mock_call):
        path = '/some/path'
        fake_file = '/path/to/uber_ontology.owl'
        ret = convert_owl_to_json(path, fake_file)
        self.assertTrue(mock_call.called)
        self.assertEqual(ret, fake_file + '.json')

    def test_initialize_robot(self):
        path = '/some/path'
        robot_info = initialize_robot(path)
        self.assertEqual(robot_info[0], os.path.join(path, "robot"))
        self.assertEqual(robot_info[1]['ROBOT_JAVA_ARGS'], '-Xmx12g -XX:+UseG1GC')
