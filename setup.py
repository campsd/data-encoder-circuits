import setuptools
from pathlib import Path

version_dict = {}
with open(Path(__file__).parents[0] / "data-circuits/_version.py") as fp:
    exec(fp.read(), version_dict)
version = version_dict["__version__"]

setuptools.setup(
    name="data-circuits",
    version=version,
    url="https://github.com/campsd/data-encoder-circuits",
    description="Python (Qiskit) implementation of the",
    license_files="license.txt",
    install_requires=["numpy", "qiskit", "scipy"],
    packages=["datacircuits"],
)
