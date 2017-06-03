import setuptools

setuptools.setup(
    name="tbl",
    version="0.0.0",
    description="Table viewing and editing tool",
    # long_description=long_description,
    url="https://github.com/sl-as-kj/tbl",
    author="slevin, kylesjohnston, alexhsamuel",
    author_email="alex@alexsamuel.net",  # ??
    license="MIT",
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Alpha",

        # Indicate who your project is intended for
        "Intended Audience :: Developers",
        # "Topic :: Software Development :: Build Tools",

        "License :: OSI Approved :: MIT License",

        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],

    # What does your project relate to?
    keywords="table",

    packages=setuptools.find_packages(exclude=[]),

    install_requires=[
        "numpy",
    ],

    package_data={},
    data_files=[],
    entry_points={},
)

