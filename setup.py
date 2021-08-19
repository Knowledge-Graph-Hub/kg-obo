from setuptools import setup

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
    name='kg-obo',
    version='0.1',
    packages=[''],
    url='https://github.com/Knowledge-Graph-Hub/kg-obo',
    license='',
    author='Justin Reese, Harry Caufield',
    author_email='justinreese@lbl.gov, jhc@lbl.gov',
    description='',

    tests_require=test_deps,

    # add package dependencies
    install_requires=[
        'kgx==1.3.0',
        'requests',
        'setuptools',
        'boto3',
        'pyyaml',
        'tqdm',
        'linkml_model'
    ]
)
