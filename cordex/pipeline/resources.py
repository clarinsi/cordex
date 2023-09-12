import os
import requests
from tqdm import tqdm
from pathlib import Path
import json
import hashlib
import zipfile
import shutil
import logging

from cordex._version import __resources_version__

logger = logging.getLogger('cordex')

# set home dir for default
HOME_DIR = str(Path.home())
CORDEX_RESOURCES_GITHUB = 'https://raw.githubusercontent.com/clarinsi/cordex-resources/'
DEFAULT_RESOURCES_URL = os.getenv('CORDEX_RESOURCES_URL', CORDEX_RESOURCES_GITHUB + 'main')
DEFAULT_RESOURCES_VERSION = os.getenv(
    'CORDEX_RESOURCES_VERSION',
    __resources_version__
)
DEFAULT_MODEL_URL = os.getenv('CORDEX_MODEL_URL', 'default')
DEFAULT_MODEL_DIR = os.getenv(
    'CORDEX_RESOURCES_DIR',
    os.path.join(HOME_DIR, 'cordex_resources')
)


def ensure_dir(dir):
    """
    Create dir in case it does not exist.
    """
    Path(dir).mkdir(parents=True, exist_ok=True)


def get_md5(path):
    """
    Get the MD5 value of a path.
    """
    data = open(path, 'rb').read()
    return hashlib.md5(data).hexdigest()


def file_exists(path, md5):
    """
    Check if the file at `path` exists and match the provided md5 value.
    """
    # if os.path.exists(path):
    #     print(f'PATH: {path} || Written md5: {md5} || Calculated md5: {get_md5(path)}')
    return os.path.exists(path) and get_md5(path) == md5


def unzip_file(filename, zipped_filename):
    """
    Unzip only one file and name it as `filename`
    """
    logger.debug(f'Unzip: {zipped_filename} to {filename} ...')
    with zipfile.ZipFile(zipped_filename) as rf:
        files = zipfile.ZipFile.infolist(rf)
        for file in files:
            with open(filename, 'wb') as wf:
                wf.write(rf.read(file.filename))


def download_file(url, path):
    """
    Download a URL into a file as specified by `path`.
    """
    verbose = logger.level in [0, 10, 20]

    # Try to get zipped file
    zipped = True
    r = requests.get(url + '.zip', stream=True)

    # Zipped file not available
    if not r.ok:
        zipped = False
        r = requests.get(url, stream=True)

    if zipped:
        normal_path = path
        path += '.zip'
    with open(path, 'wb') as f:
        file_size = int(r.headers.get('content-length'))
        default_chunk_size = 131072
        desc = 'Downloading ' + url
        with tqdm(total=file_size, unit='B', unit_scale=True, \
            disable=not verbose, desc=desc) as pbar:
            for chunk in r.iter_content(chunk_size=default_chunk_size):
                if chunk:
                    f.write(chunk)
                    f.flush()
                    pbar.update(len(chunk))

    if zipped:
        unzip_file(normal_path, path)
        os.remove(path)


def request_file(url, path, md5=None):
    """
    A complete wrapper over download_file() that also make sure the directory of
    `path` exists, and that a file matching the md5 value does not exist.
    """
    ensure_dir(Path(path).parent)
    if file_exists(path, md5):
        logger.info(f'File exists: {path}.')
        return
    download_file(url, path)
    assert(not md5 or file_exists(path, md5))


def download(
        lang='sl',
        dir=DEFAULT_MODEL_DIR,
        resources_url=DEFAULT_RESOURCES_URL,
        resources_branch=None,
        resources_version=DEFAULT_RESOURCES_VERSION
    ):


    if resources_url == DEFAULT_RESOURCES_URL and resources_branch is not None:
        resources_url = CORDEX_RESOURCES_GITHUB + resources_branch
    # Download resources.json to obtain latest packages.
    logger.debug('Downloading resource file...')
    # make request
    request_file(
        f'{resources_url}/resources_{resources_version}.json',
        os.path.join(dir, 'resources.json')
    )
    # unpack results
    try:
        resources = json.load(open(os.path.join(dir, 'resources.json')))
    except:
        raise Exception(
            f'Cannot load resource file. Please check your network connection, '
            f'or provided resource url and resource version.'
        )
    if lang not in resources:
        raise Exception(f'Unsupported language: {lang}.')

    url = resources['url']

    try:
        request_file(
            f'{url}/{resources[lang]["link"]}',
            os.path.join(dir, f'{lang}.xz'),
            md5=resources[lang]['md5']
        )
    except KeyError as e:
        raise Exception(
            f'Cannot download file at {url}/{resources[lang]["link"]}. Please recheck url.'
        ) from e
    logger.info(f'Finished downloading models and saved to {dir}.')
