from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="vidview",
    version="1.0.0",
    author="marlefranco",
    author_email="",
    description="A desktop application for inspecting video frames alongside synchronized spectral data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/marlefranco/VidView",
    packages=find_packages(),
    py_modules=["main", "constants", "data_handler", "logging_config", "main_window", "output_file", "output_writer", "viewer"],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "vidview=main:main",
        ],
    },
)
