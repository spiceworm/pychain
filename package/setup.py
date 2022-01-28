#!/usr/bin/env python
import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

requires = [
    "aiohttp>=3.8.1",
    "asyncpg>=0.25.0",
    "psycopg2-binary>=2.9.3",
    "SQLAlchemy>=1.4.31",
    "requests>=2.26.0",
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
        "Programming Language :: Python :: 3.10",
    ],
    project_urls={
        "Source": "https://github.com/ecaz-eth/pychain",
    },
)
