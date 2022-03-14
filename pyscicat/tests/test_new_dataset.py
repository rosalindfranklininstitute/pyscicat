from pathlib import Path
import urllib
import json

import requests_mock
from ..client import ScicatClient

from ..model import (
    DataFile,
    RawDataset,
    OrigDatablock,
    Ownable,
)

global test_dataset

local_url = "http://localhost:3000/api/v3/"
test_dataset_file = "../../examples/data/ingestion_simulation_dataset_ess_dataset.json"
test_dataset = None


def set_up_test_environment(mock_request):

    global test_dataset

    # load test data
    data_file_path = Path(__file__).parent.joinpath(test_dataset_file).resolve()
    with open(data_file_path, "r") as fh:
        test_dataset = json.load(fh)

    mock_request.post(
        local_url + "Users/login",
        json={"id": "a_token"},
    )

    mock_request.post(
        local_url + "Datasets",
        json={**{"pid": test_dataset["id"]}, **test_dataset["dataset"]},
    )

    encoded_pid = urllib.parse.quote_plus(test_dataset["id"])
    mock_request.post(
        local_url + "Datasets/" + encoded_pid + "/origdatablocks",
        json={
            "size": test_dataset["orig_datablock"]["size"],
            "datasetId": test_dataset["id"],
            "dataFileList": test_dataset["orig_datablock"]["dataFileList"],
        },
    )


def test_scicate_ingest_raw_dataset():
    with requests_mock.Mocker() as mock_request:
        set_up_test_environment(mock_request)
        scicat = ScicatClient(
            base_url=local_url,
            username="Zaphod",
            password="heartofgold",
        )
        assert (
            scicat._token == "a_token"
        ), "scicat client set the token given by the server"

        ownable = Ownable(ownerGroup="magrathea", accessGroups=["deep_though"])

        # Create Dataset
        dataset = RawDataset(**test_dataset["dataset"], **ownable.dict())
        created_dataset = scicat.upload_new_dataset(dataset)

        assert created_dataset["pid"] == test_dataset["id"]

        # origDatablock with DataFiles
        origDataBlock = OrigDatablock(
            size=test_dataset["orig_datablock"]["size"],
            datasetId=created_dataset["pid"],
            dataFileList=[
                DataFile(**file)
                for file in test_dataset["orig_datablock"]["dataFileList"]
            ],
            **ownable.dict()
        )
        created_origdatablock = scicat.upload_dataset_origdatablock(origDataBlock)
        assert len(created_origdatablock["dataFileList"]) == len(
            test_dataset["orig_datablock"]["dataFileList"]
        )
