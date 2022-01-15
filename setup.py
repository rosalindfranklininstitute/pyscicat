from os import path
from setuptools import setup, find_packages
import sys
import versioneer

min_version = (3, 7)
if sys.version_info < min_version:
    error = """
pyscicat does not support Python {0}.{1}.
Python {2}.{3} and above is required. Check your Python version like so:

python3 --version

This may be due to an out-of-date pip. Make sure you have pip >= 9.0.1.
Upgrade pip like so:

pip install --upgrade pip
""".format(
        *(sys.version_info[:2] + min_version)
    )
    sys.exit(error)

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as readme_file:
    readme = readme_file.read()


def read_requirements_from_here(here, filename: str = None) -> list:
    assert filename is not None, "filename as string must be provided"
    # todo, add check if filename exists, easier with pathlib.Path...
    with open(path.join(here, filename)) as requirements_file:
        # Parse requirements.txt, ignoring any commented-out lines.
        requirements = [
            line
            for line in requirements_file.read().splitlines()
            if not line.startswith("#")
        ]
    return requirements


extras_require = {}
extras_require["base"] = read_requirements_from_here(here, "requirements.txt")
extras_require["h5tools"] = read_requirements_from_here(here, "requirements-hdf5.txt")

setup(
    name="pyscicat",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Code for communicating to a SciCat backend server python",
    long_description=readme,
    author="Dylan McReynolds",
    author_email="dmcreynolds@lbl.gov",
    url="https://github.com/scicatproject/pyscicat",
    python_requires=">={}".format(".".join(str(n) for n in min_version)),
    packages=find_packages(exclude=["docs", "tests"]),
    include_package_data=True,
    install_requires=extras_require["base"],
    license="BSD (3-clause)",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
    ],
)
