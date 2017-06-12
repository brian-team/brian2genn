import sys
import os
import yaml
import glob
import shutil

try:
    from conda_build.cli.main_build import main as main_build
    from conda_build.config import get_or_merge_config
except ImportError:
    raise ImportError('Missing conda-build -- make sure "conda-build" is '
                      'installed and that you are running this script from the '
                      'conda root environment.')

recipe_path = os.path.join(os.path.dirname(__file__), '..', 'conda_recipe')

python_versions = ['2.7', '3.5', '3.6']
for python_version in python_versions:
    sys.argv = ['conda-build', '-c', 'brian-team', '--quiet',
                '--python={}'.format(python_version),
                recipe_path]
    main_build()

with open(os.path.join(recipe_path, 'meta.yaml'), 'r') as f:
    config = yaml.load(f)
    name = config['package']['name']
    version = config['package']['version']

packages_dir = get_or_merge_config(None).bldpkgs_dir

binary_package_glob = os.path.join(packages_dir,
                                   '{name}-{version}*.tar.bz2'.format(name=name,
                                                                      version=version))
binary_packages = glob.glob(binary_package_glob)
for binary_package in binary_packages:
    shutil.move(binary_package, '.')
