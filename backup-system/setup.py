#!/usr/bin/env python3
"""
Setup script for backupctl package
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="backupctl",
    version="1.0.0",
    author="Backup System Team",
    author_email="backup-team@example.com",
    description="Sistema de Backup Automatizado para PostgreSQL com AWS S3",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/postgres-backup-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: System :: Archiving :: Backup",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "backupctl=backupctl.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "backupctl": ["config/*.yaml"],
    },
)