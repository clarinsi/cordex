import re
from os import path

from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
  long_description = f.read()

# read the version from classla/_version.py
version_file_contents = open(path.join(here, 'cordex/_version.py'), encoding='utf-8').read()
VERSION = re.compile('__cordex_version__ = \'(.*)\'').search(version_file_contents).group(1)

setup(name='cordex',
  version=VERSION,
  description=u"Parser for collocability",
  long_description=long_description,
  long_description_content_type="text/markdown",
  url='https://github.com/clarinsi/cordex',
  author='CJVT',
  author_email='pypi@cjvt.si',
  license='MIT',
  packages=find_packages(),
  install_requires=[
    'conllu>=4.5.2',
    'cjvt-conversion-utils>=0.3',
    'importlib-resources>=5.4.0',
    'lxml>=4.9.1',
    'tqdm>=4.62.3',
    'zipp>=3.6.0',
    'requests>=2.21.0'
  ],
)