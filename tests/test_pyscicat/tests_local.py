from pyscicat.client import ScicatClient
from pyscicat.model import RawDataset
from datetime import datetime
import os


"""
These test_pyscicat do not use mocks and are designed to connect
 to a v4 service for Scicat backend. You can run this easily
in docker-compose following the repo
https://github.com/SciCatProject/scicatlive.
You will also need to use one of the default user accounts or add
your own.

You will need to set environmental variables for
BASE_URL - the url of your scicat service e.g. http://localhost:3000/api/v3
SCICAT_USER - the name of your scicat user.
SCICAT_PASSWORD - the password for your scicat user.
"""


def test_client():
    sci_clie = ScicatClient(base_url=os.environ["BASE_URL"],
                            token=None,
                            username=os.environ["SCICAT_USER"],
                            password=os.environ["SCICAT_PASSWORD"])
    assert type(sci_clie) == ScicatClient


def test_upload_dataset():
    sci_clie = ScicatClient(base_url=os.environ["BASE_URL"],
                            token=None, username=os.environ["SCICAT_USER"],
                            password=os.environ["SCICAT_PASSWORD"])

    payload = RawDataset(
        datasetName="a guide book",
        path="/foo/bar",
        size=42,
        owner=os.environ["SCICAT_USER"],
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
        accessGroups=[]
    )

    sci_clie.upload_new_dataset(payload)


def test_get_dataset(subtests):
    sci_clie = ScicatClient(base_url=os.environ["BASE_URL"],
                            token=None,
                            username=os.environ["SCICAT_USER"],
                            password=os.environ["SCICAT_PASSWORD"])
    datasets = sci_clie.get_datasets({"ownerGroup": "Magratheans"})
    for dataset in datasets:
        with subtests.tests(dataset=dataset):
            assert dataset["ownerGroup"] == "Magratheans"


def test_update_dataset():
    sci_clie = ScicatClient(base_url=os.environ["BASE_URL"],
                            token=None,
                            username=os.environ["SCICAT_USER"],
                            password=os.environ["SCICAT_PASSWORD"])

    pid = "PID.SAMPLE.PREFIX48a8f164-166a-4557-bafc-5a7362e39fe7"
    payload = RawDataset(
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
