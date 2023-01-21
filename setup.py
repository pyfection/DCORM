import setuptools


with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="dcorm",
    version="0.0.5",
    author="Matthias Schreiber",
    author_email="mat@pyfection.com",
    description="Data Class Object Relational Mapper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pyfection/DCORM",
    project_urls={
        "Bug Tracker": "https://github.com/pyfection/DCORM/issues"
    },
    license="MIT",
    packages=setuptools.find_packages(),
)
