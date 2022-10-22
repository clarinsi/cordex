from setuptools import setup, find_packages

setup(name='cordex',
  version='0.0.1',
  description=u"Parser for collocability",
  author=u"CJVT",
  author_email='fake@mail.com',
  license='MIT',
  packages=find_packages(),
  install_requires=[
    'conllu==4.5.2',
    'conversion-utils @ git+https://gitea.cjvt.si/generic/conversion_utils.git@2f74dfcab890f50e52426018e350faabfac11742',
    'importlib-resources==5.4.0',
    'lxml==4.9.1',
    'tqdm==4.64.1',
    'zipp==3.6.0',
    'requests==2.21.0'
  ],
)