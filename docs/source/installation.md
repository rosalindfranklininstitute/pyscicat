# Installation

At the command line
```
    $ pip install pyscicat
```

## Optional installation
There are several collections of dependency that can be install along with pyscicat. Note that the following examples add single quotes around the optional dependency to make them work on `zsh`, the default shell for MacOS.

### h5py
pyscicat includes helper utilities for ingesting NeXus files. To use these, install the hdf5 option:

```
pip install '.[hdf5]'
```

### dev
If you are developing pyscicat itself, you will want to install the dev dependencies:

```
pip install '.[dev]'
```

### docs
If you are developing pyscicat documentation and want to generate it locally on your machine:

```
pip install '.[docs]'
```

