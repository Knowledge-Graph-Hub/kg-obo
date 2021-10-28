import os
import re
from codecs import open as copen  # to use a consistent encoding
from setuptools import find_packages, setup

from post_setup.post_setup import robot_setup

here = os.path.abspath(os.path.dirname(__file__))

# get the long description from the relevant file
with copen(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


def read(*parts):
    with copen(os.path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')

__version__ = find_version('kg_obo', '__version__.py')

test_deps = [
    'pytest',
    'pytest-cov',
    'coveralls',
    'validate_version_code',
    'codacy-coverage',
    'parameterized'
]

extras = {
    'test': test_deps,
}

setup(
    name='kg_obo',
    version=__version__,
    url='https://github.com/Knowledge-Graph-Hub/kg-obo',
    license='',
    author='Justin Reese, Harry Caufield',
    author_email='justinreese@lbl.gov, jhc@lbl.gov',
    description='Code to import OBO ontologies into KGHub',
    long_description=long_description,
    python_requires='>=3.7',

    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Beta',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3'
    ],
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    tests_require=test_deps,
    # add package dependencies
    install_requires=[
        'kgx==1.5.1',
        'requests',
        'setuptools',
        'boto3',
        'botocore',
        'pyyaml',
        'tqdm',
        'click',
        'moto[s3]',
        'sphinx_rtd_theme',
        'recommonmark',
        'sh',
        'grape'
    ],
    extras_require=extras,
)

robot_setup()
