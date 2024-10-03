import setuptools
from pathlib import Path

# Get the version number
version_dict = {}
with open(Path(__file__).parents[0] / "datacircuits/_version.py") as fp:
    exec(fp.read(), version_dict)
version = version_dict["__version__"]

setuptools.setup(
    name="datacircuits",
    version=version,
    url="https://github.com/campsd/data-encoder-circuits",
    description=(
        "Python (Qiskit) implementation of circuits that can be used for "
        "loading classical data."
    ),
    license_files="LICENSE",
    install_requires=["qiskit==1.2.2", "qiskit-aer==0.15.1", "numpy", "scipy"],
    packages=["datacircuits"],
)
