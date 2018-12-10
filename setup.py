import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pywos",
    version="0.0.1",
    author="refraction-ray",
    author_email="refraction-ray@protonmail.com",
    description="Citation data export and analysis from web of science",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/refraction-ray/wos-statistics",
    packages=setuptools.find_packages(),
    install_requires=[
        'aiohttp>=3.4',
        'pandas',
        'beautifulsoup4'],
    # tests_require=['pytest'],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
