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
additional_args = sys.argv[1:]

# Run conda build purge first
sys.argv = ['conda-build', 'purge']
main_build()

# Call conda build for each python version
for python_version in python_versions:
    shutil.rmtree(os.path.join(recipe_path, '..', 'build'), ignore_errors=True)
    sys.argv = ['conda-build', '-c', 'brian-team', '--quiet',
                '--python={}'.format(python_version),
                '--no-activate'  # seems to make the build more robust on Windows
                ]
    sys.argv.extend(additional_args)
    sys.argv.append(recipe_path)
    main_build()

packages_dir = get_or_merge_config(None).bldpkgs_dir

binary_package_glob = os.path.join(packages_dir, 'brian2genn-*.tar.bz2')
binary_packages = glob.glob(binary_package_glob)

for binary_package in binary_packages:
    shutil.move(binary_package, '.')
