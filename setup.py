from setuptools import setup, find_packages
from cordex._version import __cordex_version__

setup(name='cordex',
  version=__cordex_version__,
  description=u"Parser for collocability",
  author='CLARIN.SI',
  author_email='info@clarin.si',
  license='MIT',
  packages=find_packages(),
  install_requires=[
    'conllu==4.5.2',
    'conversion-utils @ git+https://gitea.cjvt.si/generic/conversion_utils@89bcde58aa3ca01462808af74a9f39f488b1bbd0',
    'importlib-resources==5.4.0',
    'lxml==4.9.1',
    'tqdm==4.64.1',
    'zipp==3.6.0',
    'requests==2.21.0'
  ],
)