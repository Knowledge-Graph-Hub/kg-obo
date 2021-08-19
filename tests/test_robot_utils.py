from unittest import TestCase, mock

from kg_obo.robot_utils import convert_owl_to_json


class TestRobotUtils(TestCase):

    def setUp(self) -> None:
        pass

    @mock.patch('subprocess.call')
    def test_convert_owl_to_json(self, mock_call):
        ret = convert_owl_to_json("arg1", "arg2")
        self.assertTrue(mock_call.called)
        self.assertEqual(ret, "arg2.json")

