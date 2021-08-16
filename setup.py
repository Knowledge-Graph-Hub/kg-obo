from setuptools import setup

setup(
    name='obo2kghub',
    version='0.1',
    packages=[''],
    url='https://github.com/justaddcoffee/obo2kghub',
    license='',
    author='Justin Reese',
    author_email='justinreese@lbl.gov',
    description='',

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
