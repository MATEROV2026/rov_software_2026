from setuptools import find_packages
from setuptools import setup

setup(
    name='rov_interfaces',
    version='0.0.0',
    packages=find_packages(
        include=('rov_interfaces', 'rov_interfaces.*')),
)
