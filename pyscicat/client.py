from datetime import datetime
import enum

import base64
import hashlib
import logging
import json
from typing import List
import urllib

import requests

from pyscicat.model import (
    Attachment,
    Datablock,
    Dataset,
    OrigDatablock,
    RawDataset,
    DerivedDataset,
)

logger = logging.getLogger("splash_ingest")
can_debug = logger.isEnabledFor(logging.DEBUG)


class ScicatLoginError(Exception):
    """Represents an error encountered logging into SciCat"""

    def __init__(self, message):
        self.message = message


class ScicatCommError(Exception):
    """Represents an error encountered during communication with SciCat."""

    def __init__(self, message):
        self.message = message


class Severity(str, enum.Enum):
    warning = "warning"
    fatal = "fatal"


class ScicatClient:
    """Responsible for communicating with the Scicat Catamel server via http"""

    def __init__(
        self,
        base_url: str = None,
        token: str = False,
        username: str = None,
        password: str = None,
        timeout_seconds: int = None,
    ):
        """Initialize a new instance. This method attempts to create a tokenad_a
        from the provided username and password

        Parameters
        ----------
        base_url : str
            Base url. e.g. `http://localhost:3000/api/v3`
        username : str
            username to login with
        password : str
            password to login with
        timeout_seconds : [int], optional
            timeout in seconds to wait for http connections to return, by default None
        """
        if base_url[-1] != "/":
            base_url = base_url + "/"
        self._base_url = base_url
        self._timeout_seconds = (
            timeout_seconds  # we are hitting a transmission timeout...
        )
        self._username = username  # default username
        self._password = password  # default password
        self._token = token  # store token here
        self._headers = {}  # store headers
        assert self._base_url is not None, "SciCat database URL must be provided"

        logger.info(f"Starting ingestor talking to scicat at: {self._base_url}")

        if not self._token:
            assert (self._username is not None) and (
                self._password is not None
            ), "SciCat login credentials (username, password) must be provided if token is not provided"
            self._token = get_token(self._base_url, self._username, self._password)
            self._headers["Authorization"] = "Bearer {}".format(self._token)

    def _send_to_scicat(self, url, dataDict=None, cmd="post"):
        """sends a command to the SciCat API server using url and token, returns the response JSON
        Get token with the getToken method"""
        if cmd == "post":
            response = requests.post(
                url,
                params={"access_token": self._token},
                headers=self._headers,
                json=dataDict,
                timeout=self._timeout_seconds,
                stream=False,
                verify=True,
            )
        elif cmd == "delete":
            response = requests.delete(
                url,
                params={"access_token": self._token},
                headers=self._headers,
                timeout=self._timeout_seconds,
                stream=False,
            )
        elif cmd == "get":
            response = requests.get(
                url,
                params={"access_token": self._token},
                headers=self._headers,
                json=dataDict,
                timeout=self._timeout_seconds,
                stream=False,
            )
        elif cmd == "patch":
            response = requests.patch(
                url,
                params={"access_token": self._token},
                headers=self._headers,
                json=dataDict,
                timeout=self._timeout_seconds,
                stream=False,
            )
        return response

    #  Future support for samples
    # def upload_sample(self, sample):
    #     sample = {
    #         "sampleId": projected_start_doc.get('sample_id'),
    #         "owner": projected_start_doc.get('pi_name'),
    #         "description": projected_start_doc.get('sample_name'),
    #         "createdAt": datetime.isoformat(datetime.utcnow()) + "Z",
    #         "sampleCharacteristics": {},
    #         "isPublished": False,
    #         "ownerGroup": owner_group,
    #         "accessGroups": access_groups,
    #         "createdBy": self._username,
    #         "updatedBy": self._username,
    #         "updatedAt": datetime.isoformat(datetime.utcnow()) + "Z"
    #     }
    #     sample_url = f'{self._base_url}Samples'

    #     resp = self._send_to_scicat(sample_url, sample)
    #     if not resp.ok:  # can happen if sample id is a duplicate, but we can't tell that from the response
    #         err = resp.json()["error"]
    #         raise ScicatCommError(f"Error creating Sample {err}")

    def upload_dataset(self, dataset: Dataset) -> str:
        """Upload a raw or derived dataset (method is autosensing)

        Parameters
        ----------
        dataset : Dataset
            Dataset to load

        Returns
        -------
        str
            pid (or unique identifier) of the newly created dataset

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """
        if isinstance(dataset, RawDataset):
            dataset_url = self._base_url + "RawDataSets/replaceOrCreate"
        elif isinstance(dataset, DerivedDataset):
            dataset_url = self._base_url + "DerivedDatasets/replaceOrCreate"
        else:
            logging.error(
                "Dataset type not recognized (not Derived or Raw dataset instances)"
            )
        resp = self._send_to_scicat(dataset_url, dataset.dict(exclude_none=True))
        if not resp.ok:
            err = resp.json()["error"]
            raise ScicatCommError(f"Error creating dataset {err}")
        new_pid = resp.json().get("pid")
        logger.info(f"new dataset created {new_pid}")
        return new_pid

    def upload_new_dataset(self, dataset: Dataset) -> str:
        """
        Upload a new dataset. Uses the generic dataset endpoint.
        Relys on the endpoint to sense wthe dataset type

        Parameters
        ----------
        dataset : Dataset
            Dataset to create

        Returns
        -------
        dataset : Dataset
            Dataset created including the pid (or unique identifier) of the newly created dataset

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """
        dataset_url = self._base_url + "Datasets"
        resp = self._send_to_scicat(dataset_url, dataset.dict(exclude_none=True))

        if not resp.ok:
            err = resp.json()["error"]
            raise ScicatCommError(f"Error creating dataset {err}")

        new_pid = resp.json().get("pid")
        logger.info(f"new dataset created {new_pid}")

        return resp.json()

    def upload_raw_dataset(self, dataset: Dataset) -> str:
        """Upload a raw dataset

        Parameters
        ----------
        dataset : Dataset
            Dataset to load

        Returns
        -------
        str
            pid (or unique identifier) of the newly created dataset

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """
        raw_dataset_url = self._base_url + "RawDataSets/replaceOrCreate"
        resp = self._send_to_scicat(raw_dataset_url, dataset.dict(exclude_none=True))
        if not resp.ok:
            err = resp.json()["error"]
            raise ScicatCommError(f"Error creating raw dataset {err}")
        new_pid = resp.json().get("pid")
        logger.info(f"new dataset created {new_pid}")
        return new_pid

    def upload_derived_dataset(self, dataset: Dataset) -> str:
        """Upload a derived dataset

        Parameters
        ----------
        dataset : Dataset
            Dataset to upload

        Returns
        -------
        str
            pid (or unique identifier) of the newly created dataset

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """
        derived_dataset_url = self._base_url + "DerivedDataSets/replaceOrCreate"
        resp = self._send_to_scicat(
            derived_dataset_url, dataset.dict(exclude_none=True)
        )
        if not resp.ok:
            err = resp.json()["error"]
            raise ScicatCommError(f"Error creating raw dataset {err}")
        new_pid = resp.json().get("pid")
        logger.info(f"new dataset created {new_pid}")
        return new_pid

    def upsert_raw_dataset(self, dataset: Dataset, filter_fields) -> str:
        """Upsert a raw dataset

        Parameters
        ----------
        dataset : Dataset
            Dataset to load

        filter_fields
            Filters to locate where to upsert dataset

        Returns
        -------
        str
            pid (or unique identifier) of the dataset

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """
        query_results = self.get_datasets(filter_fields)
        if not query_results:
            logger.info("Dataset does not exist already, will be inserted")
        filter_fields = json.dumps(filter_fields)
        raw_dataset_url = f'{self._base_url}/RawDatasets/upsertWithWhere?where={{"where":{filter_fields}}}'
        resp = self._send_to_scicat(raw_dataset_url, dataset.dict(exclude_none=True))
        if not resp.ok:
            err = resp.json()["error"]
            raise ScicatCommError(f"Error upserting raw dataset {err}")
        new_pid = resp.json().get("pid")
        logger.info(f"dataset upserted {new_pid}")
        return new_pid

    def upsert_derived_dataset(self, dataset: Dataset, filter_fields) -> str:
        """Upsert a derived dataset

        Parameters
        ----------
        dataset : Dataset
            Dataset to upsert

        filter_fields
            Filters to locate where to upsert dataset

        Returns
        -------
        str
            pid (or unique identifier) of the dataset

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """

        query_results = self.get_datasets(filter_fields)
        if not query_results:
            logger.info("Dataset does not exist already, will be inserted")
        filter_fields = json.dumps(filter_fields)
        dataset_url = f'{self._base_url}/DerivedDatasets/upsertWithWhere?where={{"where":{filter_fields}}}'
        resp = self._send_to_scicat(dataset_url, dataset.dict(exclude_none=True))
        if not resp.ok:
            err = resp.json()["error"]
            raise ScicatCommError(f"Error upserting derived dataset {err}")
        new_pid = resp.json().get("pid")
        logger.info(f"dataset upserted {new_pid}")
        return new_pid

    def upload_datablock(self, datablock: Datablock, datasetType: str = "RawDatasets"):
        """Upload a Datablock

        Parameters
        ----------
        datablock : Datablock
            Datablock to upload

        Returns
        -------
        datablock : Datablock
            The created Datablock with id

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """

        url = (
            self._base_url
            + f"{datasetType}/{urllib.parse.quote_plus(datablock.datasetId)}/origdatablocks"
        )
        resp = self._send_to_scicat(url, datablock.dict(exclude_none=True))
        if not resp.ok:
            err = resp.json()["error"]
            raise ScicatCommError(f"Error creating datablock. {err}")

        return resp.json()

    def upload_dataset_origdatablock(self, origdatablock: OrigDatablock) -> dict:
        """
        Post SciCat Dataset OrigDatablock

        Parameters
        ----------
        origdatablock :
            The OrigDatablock to create

        Returns
        -------
        dict
            The created OrigDatablock with id

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned

        """

        encoded_pid = urllib.parse.quote_plus(origdatablock.datasetId)
        endpoint = "Datasets/" + encoded_pid + "/origdatablocks"
        url = self._base_url + endpoint

        resp = self._send_to_scicat(url, origdatablock.dict(exclude_none=True))
        if not resp.ok:
            err = resp.json()["error"]
            raise ScicatCommError(f"Error creating dataset original datablock. {err}")

        return resp.json()

    def upload_attachment(
        self, attachment: Attachment, datasetType: str = "RawDatasets"
    ):
        """Upload an Attachment.  Note that datasetType can be provided to determine the type of dataset
        that this attachment is attached to. This is required for creating the url that SciCat uses.

        Parameters
        ----------
        attachment : Attachment
            Attachment to upload

        datasetType : str
            Type of dataset to upload to, default is `RawDatasets`
        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """
        url = (
            self._base_url
            + f"{datasetType}/{urllib.parse.quote_plus(attachment.datasetId)}/attachments"
        )
        logging.debug(url)
        resp = requests.post(
            url,
            params={"access_token": self._token},
            timeout=self._timeout_seconds,
            stream=False,
            json=attachment.dict(exclude_none=True),
            verify=True,
        )
        if not resp.ok:
            err = resp.json()["error"]
            raise ScicatCommError(f"Error  uploading thumbnail. {err}")

    def get_datasets_full_query(self, skip=0, limit=25, query_fields=None):
        """Gets datasets using the fullQuery mechanism of SciCat. This is
        appropriate for cases where might want paging and cases where you want to perform
        a text search on the Datasets collection. The full features of fullQuery search
        are beyond this document.

        There is no known mechanism to query for fields that are missing or contain a
        a null value.

        To query based on the full text search, send `{"text": "<text to query"}` as query field

        Parameters
        ----------
        skip : int
            number of items to skip

        limit : int
            number of items to return

        query_fields : dict
            dictionary of terms to send to the query (must be json serializable)

        """
        if not query_fields:
            query_fields = {}
        query_fields = json.dumps(query_fields)
        query = f'fields={query_fields}&limits={{"skip":{skip},"limit":{limit},"order":"creationTime:desc"}}'

        url = f"{self._base_url}/Datasets/fullquery?{query}"
        response = self._send_to_scicat(url, cmd="get")
        if not response.ok:
            err = response.json()["error"]
            logger.error(f'{err["name"]}, {err["statusCode"]}: {err["message"]}')
            return None
        return response.json()

    def get_datasets(self, filter_fields=None) -> List[Dataset]:
        """Gets datasets using the simple fiter mechanism. This
        is appropriate when you do not require paging or text search, but
        want to be able to limit results based on items in the Dataset object.

        For example, a search for Datasets of a given proposalId would have
        ```python
        filterField = {"proposalId": "1234"}
        ```
        A search for Datasets  with no proposalId would be:
        ```python
        filterField = {"proposalId": ""}
        ```

        Parameters
        ----------
        filter_fields : dict
            Dictionary of filtering fields. Must be json serializable.
        """
        if not filter_fields:
            filter_fields = {}

        filter_fields = json.dumps(filter_fields)
        url = f'{self._base_url}/Datasets/?filter={{"where":{filter_fields}}}'
        response = self._send_to_scicat(url, cmd="get")
        if not response.ok:
            err = response.json()["error"]
            logger.error(f'{err["name"]}, {err["statusCode"]}: {err["message"]}')
            return None
        return response.json()

    # this method is future, needs testing.
    # def update_dataset(self, pid, fields: Dict):
    #     response = self._send_to_scicat(
    #         f"{self._base_url}/Datasets", dataDict=fields, cmd="patch"
    #     )
    #     if not response.ok:
    #         err = response.json()["error"]
    #         logger.error(f'{err["name"]}, {err["statusCode"]}: {err["message"]}')
    #         return None
    #     return response.json()

    def get_instrument(self, pid: str = None, name: str = None) -> dict:
        """
        Get an instrument by pid or by name.
        If pid is provided it takes priority over name.

        Parameters
        ----------
        pid : str
            Pid of the instrument

        name : str
            The name of the instrument

        Returns
        -------
        dict
            The instrument with the requested name
        """

        if pid:
            encoded_pid = urllib.parse.quote_plus(pid)
            endpoint = "/Instruments/{}".format(encoded_pid)
            url = self._base_url + endpoint
        elif name:
            endpoint = "/Instruments/findOne"
            query = json.dumps({"where": {"name": {"like": name}}})
            url = self._base_url + endpoint + "?" + query
        else:
            logger.error(
                "Invalid instrument pid and/or name. You must specify instrument pid or name"
            )
            return None

        response = self._send_to_scicat(url, cmd="get")
        if not response.ok:
            err = response.json()["error"]
            logger.error(f'{err["name"]}, {err["statusCode"]}: {err["message"]}')
            return None
        return response.json()

    def get_sample(self, pid: str = None) -> dict:
        """
        Get an sample by pid.

        Parameters
        ----------
        pid : str
            The pid of the sample

        Returns
        -------
        dict
            The sample with the requested pid
        """

        encoded_pid = urllib.parse.quote_plus(pid)
        endpoint = "/Samples/{}".format(encoded_pid)
        url = self._base_url + endpoint
        response = self._send_to_scicat(url, cmd="get")
        if not response.ok:
            err = response.json()["error"]
            logger.error(f'{err["name"]}, {err["statusCode"]}: {err["message"]}')
            return None
        return response.json()

    def get_proposal(self, pid: str = None) -> dict:
        """
        Get proposal by pid.

        Parameters
        ----------
        pid : str
            The pid of the proposal

        Returns
        -------
        dict
            The proposal with the requested pid
        """

        endpoint = "/Proposals/"
        url = self._base_url + endpoint + pid
        response = self._send_to_scicat(url, cmd="get")
        if not response.ok:
            err = response.json()["error"]
            logger.error(f'{err["name"]}, {err["statusCode"]}: {err["message"]}')
            return None
        return response.json()


def get_file_size(pathobj):
    filesize = pathobj.lstat().st_size
    return filesize


def get_checksum(pathobj):
    with open(pathobj) as file_to_check:
        # pipe contents of the file through
        return hashlib.md5(file_to_check.read()).hexdigest()


def encode_thumbnail(filename, imType="jpg"):
    logging.info(f"Creating thumbnail for dataset: {filename}")
    header = "data:image/{imType};base64,".format(imType=imType)
    with open(filename, "rb") as f:
        data = f.read()
    dataBytes = base64.b64encode(data)
    dataStr = dataBytes.decode("UTF-8")
    return header + dataStr


def get_file_mod_time(pathobj):
    # may only work on WindowsPath objects...
    # timestamp = pathobj.lstat().st_mtime
    return str(datetime.fromtimestamp(pathobj.lstat().st_mtime))


def from_token(base_url: str, token: str):
    return ScicatClient(base_url, token)


def from_credentials(base_url: str, username: str, password: str):
    token = get_token(base_url, username, password)
    return from_token(base_url, token)


def get_token(base_url, username, password):
    """logs in using the provided username / password combination
    and receives token for further communication use"""
    logger.info(f" Getting new token for user {username}")
    if base_url[-1] != "/":
        base_url = base_url + "/"
    response = requests.post(
        base_url + "Users/login",
        json={"username": username, "password": password},
        stream=False,
        verify=True,
    )
    if not response.ok:
        logger.error(f" ** Error received: {response}")
        err = response.json()["error"]
        logger.error(f' {err["name"]}, {err["statusCode"]}: {err["message"]}')
        raise ScicatLoginError(response.content)

    data = response.json()
    # print("Response:", data)
    token = data["id"]  # not sure if semantically correct
    logger.info(f" token: {token}")
    return token
