import sys
import os
import glob
import time
import pkg_resources

from binstar_client.scripts.cli import main
from binstar_client.errors import BinstarError

assert len(sys.argv) == 2, 'expected the tag (release version) as a command line argument'
tag = sys.argv[1]

version = pkg_resources.parse_version(tag)

token = os.environ['ANACONDA_TOKEN']
filenames = glob.glob('*.tar.bz2')

# Uploading sometimes fails due to server or network errors -- we try it five
# times before giving up
attempts = 5
options = ['-t', token, 'upload',
           '-u', 'brian-team']
if version.is_prerelease:
    options.extend(['--channel', 'dev'])
for filename in filenames:
    for attempt in range(attempts):
        try:
            main(args=options+[filename])
            break
        except BinstarError as ex:
            print('Something did not work (%s).' % str(ex))
            if attempt < attempts - 1:
                print('Trying again in 10 seconds...')
                time.sleep(10)
            else:
                print('Giving up...')
                raise ex
