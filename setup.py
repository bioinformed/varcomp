from setuptools import setup, find_packages

setup(
    name="vcomp",
    version="0.1.0",
    packages=find_packages(),
    install_requires=['pysam', 'matplotlib', 'matplotlib_venn', 'path.py']
)
