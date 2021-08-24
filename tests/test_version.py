import os
import re
from unittest import TestCase
from codecs import open as copen  # to use a consistent encoding


def read(*parts):
    here = os.path.abspath(os.path.dirname(__file__))
    with copen(os.path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)


class TestVersion(TestCase):

    def setUp(self) -> None:
        pass

    def test_version(self) -> None:
        self.assertEqual(str(0.1), find_version('../kg_obo', '__version__.py') )







