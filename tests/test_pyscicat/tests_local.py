from pyscicat.client import ScicatClient
from pyscicat.model import RawDataset, Ownable, Dataset, DatasetType
from datetime import datetime
import os
import requests
import json

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

sci_clie = ScicatClient(base_url=os.environ["BASE_URL"],
                        token=None,
                        username=os.environ["SCICAT_USER"],
                        password=os.environ["SCICAT_PASSWORD"])
def test_client():

    assert type(sci_clie) == ScicatClient


def test_upload_dataset_requests():

    """ Testing if we can see a dataset in Scicat if it has been uploaded via requests but has been created via RawDataset model
      """

    ownable = Ownable( ownerGroup="Magratheans", accessGroups=[])
    payload = RawDataset(
        datasetName="a new guide book",
        path="/foo/bar",
        size=42,
        packedSize=0,
        owner=os.environ["SCICAT_USER"],
        contactEmail="slartibartfast@magrathea.org",
        creationLocation="Magrathea",
        creationTime=datetime.strftime(datetime.now(), format="%y-%m-%dT%H:%M:%S.%sZ"),
        instrumentId="earth",
        proposalId="deepthought",
        dataFormat="planet",
        principalInvestigator="A. Mouse",
        sourceFolder="/foo/bar",
        scientificMetadata={"type": "string", "value":{"a": "field"}},
        sampleId="gargleblaster",
        type="raw",
        ownerEmail="scicatingestor@your.site",
        sourceFolderHost="s3.heartofgold.org",
        endTime=datetime.isoformat(datetime.now()),
        techniques = [],
        numberOfFiles=0,
        numberOfFilesArchived=0,
        **ownable.dict()
    )



    r = requests.request("post", os.environ["BASE_URL"] + '/auth/login', json=dict(username='ingestor', password='aman'))

    token = r.json()['id']

    prep_dict ={ k: v if v is not None else "None" for k, v in  payload.dict().items()}

    drop_list = ["updatedAt", "createdBy", "pid", "updatedBy", "createdAt", "history"]
    for k in drop_list:
      del prep_dict[k]

    r = requests.request('post', os.environ["BASE_URL"] + '/datasets', json= payload.dict(exclude_none=True),
                         headers={'Authorization': f'Bearer {token}'})
   # r = requests.request('post', os.environ["BASE_URL"] + '/datasets', json= prep_dict,
   #                      headers={'Authorization': f'Bearer {token}'})
    # with open("prep_dict.json", 'w') as f:
    #     json.dump(prep_dict, f)

    q = requests.request('get', os.environ["BASE_URL"] + '/Datasets',
                         headers={'Authorization': f'Bearer {sci_clie._token}'})

    assert payload.datasetName in q.text


def test_upload_dataset_sci_cli():
    """ Testing if we can see a dataset in Scicat if it has been uploaded via pyscicat but is created from a dictionary.
    had to change _send_to_scicat so that it does not try to cast a dictionary to a dictionary.
    """
    sci_clie = ScicatClient(base_url=os.environ["BASE_URL"],
                            token=None, username=os.environ["SCICAT_USER"],
                            password=os.environ["SCICAT_PASSWORD"])

    payload = {
        "owner": "ingestor",
        "ownerGroup": "Magratheans",
        "accessGroups": [],
        "dataFormat": "directory",
        "principalInvestigator": "slartibartfast",
        "endTime": "2020-04-08T08:10:07.553Z",
        "creationLocation": "my_test_instrument",
        "scientificMetadata": {},
        "owner": "ingestor",
        "ownerEmail": "slartibartfast@magrathea.com",
        "orcidOfOwner": "https://orcid.org/0000-0000-0000-0000",
        "contactEmail": "scicatingestor@org.org",
        "sourceFolder": "new_test_4.txt",
        "sourceFolderHost": "s3.amazonaws.com",
        "size": 0,
        "packedSize": 0,
        "creationTime": "2023-03-08T08:10:06.713Z",
        "type": "raw",
        "validationStatus": "string",
        "keywords": [],
        "description": "Description of my example dataset.",
        "datasetName": "Example Dataset",
        "classification": "AV=medium,CO=low",
        "license": "string",
        "version": "rfi-file-monitor-0.2.0:extensions-0.1.3",
        "isPublished": True,
        "datasetlifecycle": {
            "archivable": True,
            "retrievable": True,
            "publishable": True,
            "dateOfDiskPurging": "2020-04-08T08:10:06.713Z",
            "archiveRetentionTime": "2020-04-08T08:10:06.713Z",
            "dateOfPublishing": "2020-04-08T08:10:06.713Z",
            "isOnCentralDisk": True,
            "archiveStatusMessage": "archive job sent",
            "retrieveStatusMessage": "retrieve job sent",
            "archiveReturnMessage": {},
            "retrieveReturnMessage": {},
            "exportedTo": "string",
            "retrieveIntegrityCheck": True
        },
        # "history": [],
        "instrumentId": "string",
        "techniques": [
            {
                "pid": "string",
                "name": "Example technique"
            }
        ]}

    sci_clie._call_endpoint('post', 'Datasets', payload)

    r = requests.request('get', os.environ["BASE_URL"] + '/Datasets',
                         headers={'Authorization': f'Bearer {sci_clie._token}'})

    assert payload["datasetName"] in r.text
    print(r.text)

def test_minimal_upload():
    """ Creating a minimal payload to see if we can replicate the error we are getting in raw dataset.
    """
    sci_clie = ScicatClient(base_url=os.environ["BASE_URL"],
                            token=None, username=os.environ["SCICAT_USER"],
                            password=os.environ["SCICAT_PASSWORD"])
    payload = {
        "owner": "ingestor",
        "ownerGroup": "Magratheans",
        "accessGroups": [],
        "dataFormat": "directory",
        "principalInvestigator": "slartibartfast",
        # "endTime": "2020-04-08T08:10:07.553Z",
        "creationLocation": "my_test_instrument",
        # "scientificMetadata": {},
        "owner": "ingestor",
        #  "ownerEmail": "slartibartfast@magrathea.com",
        # "orcidOfOwner": "https://orcid.org/0000-0000-0000-0000",
        "contactEmail": "scicatingestor@org.org",
        "sourceFolder": "new_test_4.txt",
        # "sourceFolderHost": "s3.amazonaws.com",
        "size": 0,
        # "packedSize": 0,
        "creationTime": "2023-03-08T08:10:06.713Z",
        "type": "raw",
        # "validationStatus": "string",
        # "keywords": [],
        # "description": "Description of my example dataset.",
        "datasetName": "Minimal Dataset",
        # "classification": "AV=medium,CO=low",
        # "license": "string",
        # "version": "rfi-file-monitor-0.2.0:extensions-0.1.3",
        # "isPublished": True,
        # "datasetlifecycle": {
        #     "archivable": True,
        #     "retrievable": True,
        #     "publishable": True,
        #     "dateOfDiskPurging": "2020-04-08T08:10:06.713Z",
        #     "archiveRetentionTime": "2020-04-08T08:10:06.713Z",
        #     "dateOfPublishing": "2020-04-08T08:10:06.713Z",
        #     "isOnCentralDisk": True,
        #     "archiveStatusMessage": "archive job sent",
        #     "retrieveStatusMessage": "retrieve job sent",
        #     "archiveReturnMessage": {},
        #     "retrieveReturnMessage": {},
        #     "exportedTo": "string",
        #     "retrieveIntegrityCheck": True
        # },
        # # "history": [],
        # "instrumentId": "string",
        # "techniques": [
        #     {
        #         "pid": "string",
        #         "name": "Example technique"
        #     }
        #     ]
    }

    with open("native_dict.json", 'w') as f:
        json.dump(payload, f)

    sci_clie._call_endpoint('post', 'Datasets', payload)

    r = requests.request('get', os.environ["BASE_URL"] + '/Datasets',
                         headers={'Authorization': f'Bearer {sci_clie._token}'})


# def test_get_dataset(subtests):
#     sci_clie = ScicatClient(base_url=os.environ["BASE_URL"],
#                             token=None,
#                             username=os.environ["SCICAT_USER"],
#                             password=os.environ["SCICAT_PASSWORD"])
#     datasets = sci_clie.get_datasets({"owner": "ingestor"})
#     for dataset in datasets:
#         with subtests.tests(dataset=dataset):
#             assert dataset["ownerGroup"] == "Magratheans"


# def test_update_dataset():
#     sci_clie = ScicatClient(base_url=os.environ["BASE_URL"],
#                             token=None,
#                             username=os.environ["SCICAT_USER"],
#                             password=os.environ["SCICAT_PASSWORD"])
#
#
#     payload = RawDataset(
#         size=142,
#         owner="slartibartfast",
#         ownerGroup="Magrateheans",
#         contactEmail="slartibartfast@magrathea.org",
#         creationLocation="magrathea",
#         creationTime=datetime.isoformat(datetime.now()),
#         instrumentId="earth",
#        #proposalId="deepthought",
#         dataFormat="planet",
#         principalInvestigator="A. Mouse",
#         sourceFolder="/foo/bar",
#         scientificMetadata={"a": "field"},
#         sampleId="gargleblaster",
#         accessGroups=["Vogons"]
#     )
#     sci_clie.update_dataset(payload, pid)


