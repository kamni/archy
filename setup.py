from setuptools import find_packages, setup

from archy.main import _VERSION_

setup(
    name='archy',
    description='Command line tool for archiving files based on group membership',
    version=_VERSION_,
    author='J Leadbetter',
    author_email='j@jleadbetter.com',
    url='https://github.com/kamni/archy',
    licensce='MIT',
    install_requires=[
        'fasteners==0.14.1',
        'filelock==3.8.2',
        'pydantic==1.7.4',
        'python-json-logger==2.0.1',
    ],
    packages=find_packages(exclude=['tests']),
    entry_points={
        'console_scripts': ['archy = archy.main:main'],
    },
)
