from setuptools import setup, find_packages

setup(
    name="orbio",
    version="0.1.0",
    description="A privacy-first Linux browser with radial UI",
    author="FireRam",
    license="GPLv3",
    packages=find_packages(),
    python_requires=">=3.12",
    install_requires=[
        "PyQt6>=6.6.0",
        "PyQt6-WebEngine>=6.6.0",
    ],
    entry_points={
        "console_scripts": [
            "orbio=orbio.main:main",
        ],
    },
    package_data={
        "orbio": ["assets/*", "assets/icons/*", "themes/*.json"],
    },
)
