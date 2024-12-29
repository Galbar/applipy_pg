from setuptools import setup, find_packages
from distutils.util import convert_path
from os import path

ns: dict[str, str] = {}
ver_path = convert_path("applipy_pg/version.py")
with open(ver_path) as ver_file:
    exec(ver_file.read(), ns)
version = ns["__version__"]

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="applipy_pg",
    url="https://gitlab.com/applipy/applipy_pg",
    project_urls={
        "Source": "https://gitlab.com/applipy/applipy_pg",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
    ],
    description="An applipy library for working with PostgreSQL.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="Apache 2.0",
    author="Alessio Linares",
    author_email="mail@alessio.cc",
    version=version,
    packages=find_packages(exclude=["docs", "tests"]),
    data_files=[],
    python_requires=">=3.12",
    install_requires=[
        "applipy>=2.4.0,<3.0.0",
        "aiopg>=1.4.0,<2.0.0",
    ],
    scripts=[],
    package_data={"applipy_pg": ["py.typed"]},
    extras_require={
        "dev": [
            "docker==7.1.0",
            # This is the version required for docker to work: https://github.com/docker/docker-py/issues/3256
            "requests==2.32.3",
            "pytest==7.4.3",
            "pytest-asyncio==0.23.2",
            "pytest-cov==4.1.0",
            "mypy==1.8.0",
            "flake8==6.1.0",
            "testcontainers-postgres==0.0.1rc1",
        ],
    },
)
