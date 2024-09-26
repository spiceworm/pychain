#!/usr/bin/env python
import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

requires = [
    "aiohttp>=3.8.3",
    "requests>=2.28.1",
]

about = {}
with open(os.path.join(here, "pychain", "__version__.py"), encoding="utf-8") as f:
    exec(f.read(), about)

with open("README.md", encoding="utf-8") as f:
    readme = f.read()

setup(
    name=about["__title__"],
    version=about["__version__"],
    description=about["__description__"],
    long_description=readme,
    long_description_content_type="text/markdown",
    author=about["__author__"],
    author_email=about["__author_email__"],
    url=about["__url__"],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    license=about["__license__"],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    project_urls={
        "Source": "https://github.com/spiceworm/pychain",
    },
)
