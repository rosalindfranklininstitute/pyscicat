import unittest
from ..client import ScicatClient
from ..model import RawDataset
from datetime import datetime
import os

class TestClientLocally(unittest.TestCase):
    """
    These tests do not use mocks and are designed to connect to a v4 service for Scicat backend. You can run this easily
    in docker-compose following the repo https://github.com/SciCatProject/scicatlive. You will also need to use one of
    the default user accounts or add your own.

    You will need to set environmental variables for
    BASE_URL - the url of your scicat service e.g. http://localhost:3000/api/v3
    SCICAT_USER - the name of your scicat user.
    SCICAT_PASSWORD - the password for your scicat user.
    """

    def test_client(self):
        sci_clie = ScicatClient(base_url=os.environ["BASE_URL"], token=None, username=os.environ["SCICAT_USER"], password="SCICAT_PASSWORD")
        self.assertIsInstance(sci_clie, ScicatClient)
        print(sci_clie._token)



    def test_upload_dataset(self):
        sci_clie = ScicatClient(base_url=os.environ["BASE_URL"], token=None, username=os.environ["SCICAT_USER"], password="SCICAT_PASSWORD")

        payload = RawDataset(
            datasetName="a guide book",
            path="/foo/bar",
            size=42,
            owner=os.environ["SCICAT_USER"],
            ownerGroup="Magrateheans",
            contactEmail="slartibartfast@magrathea.org",
            creationLocation="magrathea",
            creationTime= datetime.isoformat(datetime.now()),
            instrumentId="earth",
            proposalId="deepthought",
            dataFormat="planet",
            principalInvestigator="A. Mouse",
            sourceFolder="/foo/bar",
            scientificMetadata={"a": "field"},
            sampleId="gargleblaster",
            accessGroups=[]
        )

        sci_clie.upload_new_dataset(payload)


    def  test_replace_dataset(self):
        sci_clie = ScicatClient(base_url=os.environ["BASE_URL"], token=None, username=os.environ["SCICAT_USER"], password="SCICAT_PASSWORD")

        pid="PID.SAMPLE.PREFIX48a8f164-166a-4557-bafc-5a7362e39fe7"
        payload= RawDataset(
            size=142,
            owner="slartibartfast",
            ownerGroup="Magrateheans",
            contactEmail="slartibartfast@magrathea.org",
            creationLocation="magrathea",
            creationTime=datetime.isoformat(datetime.now()),
            instrumentId="earth",
            proposalId="deepthought",
            dataFormat="planet",
            principalInvestigator="A. Mouse",
            sourceFolder="/foo/bar",
            scientificMetadata={"a": "field"},
            sampleId="gargleblaster",
            accessGroups=["Vogons"]
        )
        sci_clie.update_dataset(payload, pid)


    def test_get_dataset(self):
        sci_clie = ScicatClient(base_url=os.environ["BASE_URL"], token=None, username=os.environ["SCICAT_USER"], password="SCICAT_PASSWORD")
        datasets = sci_clie.get_datasets({"owner":os.environ["SCICAT_USER"]})
        with self.subTest(dataset=datasets):
            self.assertEqual(dataset["owner"], os.environ["SCICAT_USER"])
