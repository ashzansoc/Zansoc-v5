"""Setup script for ZanSoc CLI."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="zansoc-cli",
    version="1.0.0",
    description="ZanSoc Provider Onboarding CLI - Join the distributed compute network",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ZanSoc Team",
    author_email="support@zansoc.com",
    url="https://github.com/zansoc/zansoc-beta",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "zansoc=zansoc_cli.seamless_cli:main",
            "zansoc-onboard=zansoc_cli.seamless_cli:main",
            "zansoc-cli=zansoc_cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Networking",
    ],
    keywords="distributed-computing ray cluster provider onboarding",
    project_urls={
        "Bug Reports": "https://github.com/zansoc/zansoc-beta/issues",
        "Source": "https://github.com/zansoc/zansoc-beta",
        "Documentation": "https://docs.zansoc.com",
    },
)