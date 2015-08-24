from setuptools import setup, find_packages
from runfolder import __version__
import os

def read_file(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='runfolder',
    version=__version__,
    description="Micro-service for managing runfolders",
    long_description=read_file('README'),
    keywords='bioinformatics',
    author='SNP&SEQ Technology Platform, Uppsala University',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': ['runfolder-ws = runfolder.app:start']
    }
)
