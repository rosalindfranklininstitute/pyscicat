import unittest

# these need to be loaded at the beginning to avoid errors related to relative imports (ImportWarning in h5py)
# might be related to the change of import style for Python 3.7+. Tested on Python 3.9 at 20220114
from pathlib import Path

# these packages are failing to import in McHat if they are not loaded here:
from ..extractscientificmetadata import extractScientificMetadata
from ..h5tools import h5Get, h5GetDict


class testh5tools(unittest.TestCase):
    def test_readValue(self):
        p = Path(
            "hdf5scicattools/_tests/testdata/cylinderHex_r5_s12_T50_large_ranW_0p5.nxs"
        )
        v = h5Get(p, "/sasentry1/sasdata1/I")
        self.assertTrue(v != "none", "Did not extract value")

    def test_readAttribute(self):
        p = Path(
            "hdf5scicattools/_tests/testdata/cylinderHex_r5_s12_T50_large_ranW_0p5.nxs"
        )
        v = h5Get(p, "/sasentry1/sasdata1@timestamp")
        self.assertTrue(v != "none", "Did not extract attribute")

    def test_readMixedDict(self):
        p = Path(
            "hdf5scicattools/_tests/testdata/cylinderHex_r5_s12_T50_large_ranW_0p5.nxs"
        )
        v = h5GetDict(
            p,
            {
                "/sasentry1/sasdata1@timestamp": 123,
                "/sasentry1/sasdata1/I": 0,
                "/sasentry1/sasdata1/I@units": "inverse amps",
            },
        )
        self.assertTrue(
            v["/sasentry1/sasdata1/I@units"] != "inverse amps",
            "Did not extract unit attribute",
        )
        self.assertTrue(
            v["/sasentry1/sasdata1/I"] != 0, "Did not extract intensity value(s)"
        )


class testESMD(unittest.TestCase):
    def test_readMetadata_withroot(self):
        p = Path(
            "hdf5scicattools/_tests/testdata/cylinderHex_r5_s12_T50_large_ranW_0p5.nxs"
        )
        assert p.exists(), f"HDF5/NeXus test file: {p.as_posix()} cannot be found"
        resultDict = extractScientificMetadata(
            p, excludeRootEntry=True, skipKeyList=["sasdata1"]
        )
        self.assertIsNotNone(
            resultDict, "extractScientificMetadata has not returned anything"
        )

        # make sure the root entry has been skipped
        self.assertTrue(
            "sasentry1" not in resultDict.keys(), "Root entry was not excluded"
        )

        # make sure the skipKeyList item has been skipped
        self.assertTrue("sasdata1" not in resultDict.keys(), "skipKey was not skipped")


if __name__ == "__main__":
    unittest.main()
