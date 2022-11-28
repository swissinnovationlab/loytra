import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="loytra",
    version="1.0.0",
    author="mfatiga",
    author_email="",
    description="LOYTRA - Linux Os pYThon Repository Assistant",
    long_description=long_description,
    url="https://github.com/swissinnovationlab/loytra",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'loytra = loytra_cli.cli:run',
            'loytra-service-runner = loytra_modules._service_runner:run_systemd_service',
        ],
    },
    install_requires=[
        # service control libs
        'sdnotify',

        # cli libs
        'typer',
        'gitpython'
    ],
)

