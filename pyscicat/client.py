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
    PublishedData,
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

    def datasets_replace(self, dataset: Dataset) -> str:
        """
        Create a new dataset or update an existing one
        This function was renamed.
        It is still accessible with the original name for backward compatibility
        The original names were upload_dataset replace_datasets
        This function is obsolete and it will be remove in next relesases


        Parameters
        ----------
        dataset : Dataset
            Dataset to create or update

        Returns
        -------
        str
            pid of the dataset
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

    """
        Upload or create a new dataset
        Original name, kept for for backward compatibility
    """
    upload_dataset = datasets_replace
    replace_dataset = datasets_replace

    def datasets_create(self, dataset: Dataset) -> str:
        """
        Upload a new dataset. Uses the generic dataset endpoint.
        Relies on the endpoint to sense the dataset type
        This function was renamed.
        It is still accessible with the original name for backward compatibility
        The original name were create_dataset and upload_new_dataset

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

    """
        Upload a new dataset
        Original name, kept for for backward compatibility
    """
    upload_new_dataset = datasets_create
    create_dataset = datasets_create

    def datasets_raw_replace(self, dataset: Dataset) -> str:
        """
        Create a new raw dataset or update an existing one
        This function was renamed.
        It is still accessible with the original name for backward compatibility
        The original names were repalce_raw_dataset and upload_raw_dataset
        THis function is obsolete and it will be removed in future releases

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

    """
        Upload a raw dataset
        Original name, kept for for backward compatibility
    """
    upload_raw_dataset = datasets_raw_replace
    replace_raw_dataset = datasets_raw_replace

    def datasets_derived_replace(self, dataset: Dataset) -> str:
        """
        Create a new derived dataset or update an existing one
        This function was renamed.
        It is still accessible with the original name for backward compatibility
        The original names were replace_derived_dataset and upload_derived_dataset


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

    def update_dataset(self, dataset: Dataset, pid) -> str:
        """Updates an existing dataset

        Parameters
        ----------
        dataset : Dataset
            Dataset to update

        pid
            pid (or unique identifier) of dataset being updated

        Returns
        -------
        str
            pid (or unique identifier) of the dataset
        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """
        if pid:
            encoded_pid = urllib.parse.quote_plus(pid)
            endpoint = "Datasets/{}".format(encoded_pid)
            url = self._base_url + endpoint
        else:
            logger.error("No pid given. You must specify a dataset pid.")
            return None

        resp = self._send_to_scicat(url, dataset.dict(exclude_none=True), cmd="patch")
        if not resp.ok:
            err = resp.json()["error"]
            raise ScicatCommError(f"Error updating dataset {err}")
        pid = resp.json().get("pid")
        logger.info(f"dataset updated {pid}")
        return pid

    def datasets_datablock_create(
        self, datablock: Datablock, datasetType: str = "RawDatasets"
    ):
        """
        Create a new datablock for a dataset.
        The dataset can be both Raw or Derived.
        It is still accessible with the original name for backward compatibility
        The original names were create_dataset_datablock and upload_datablock
        This function is obsolete and will be removed in future releases
        Function datasets_origdatablock_create should be used.

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

    """
        Upload a Datablock
        Original name, kept for for backward compatibility
    """
    upload_datablock = datasets_datablock_create
    create_dataset_datablock = datasets_datablock_create

    def datasets_origdatablock_create(self, origdatablock: OrigDatablock) -> dict:
        """
        Create a new SciCat Dataset OrigDatablock
        This function has been renamed.
        It is still accessible with the original name for backward compatibility
        The original names were create_dataset_origdatablock and upload_dataset_origdatablock

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

    """
        Create a new SciCat Dataset OrigDatablock
        Original name, kept for for backward compatibility
    """
    upload_dataset_origdatablock = datasets_origdatablock_create
    create_dataset_origdatablock = datasets_origdatablock_create

    def datasets_attachment_create(
        self, attachment: Attachment, datasetType: str = "RawDatasets"
    ):
        """
        Create a new Attachment for a dataset.
        Note that datasetType can be provided to determine the type of dataset
        that this attachment is attached to. This is required for creating the url that SciCat uses.
        This function has been renamed.
        It is still accessible with the original name for backward compatibility
        The original names were create_dataset_attachment and upload_attachment

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

    """
        Create a new attachement for a dataset
        Original name, kept for for backward compatibility
    """
    upload_attachment = datasets_attachment_create
    create_dataset_attachment = datasets_attachment_create

    def datasets_find(self, skip=0, limit=25, query_fields=None):
        """
        Gets datasets using the fullQuery mechanism of SciCat. This is
        appropriate for cases where might want paging and cases where you want to perform
        a text search on the Datasets collection. The full features of fullQuery search
        are beyond this document.

        There is no known mechanism to query for fields that are missing or contain a
        a null value.

        To query based on the full text search, send `{"text": "<text to query"}` as query field

        This function was renamed.
        It is still accessible with the original name for backward compatibility
        The original name was find_datasets_full_query and get_datasets_full_query

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

    """
        find a set of datasets according the full query provided
        Original name, kept for for backward compatibility
    """
    get_datasets_full_query = datasets_find
    find_datasets_full_query = datasets_find

    def datasets_get_many(self, filter_fields=None) -> List[Dataset]:
        """
        Gets datasets using the simple fiter mechanism. This
        is appropriate when you do not require paging or text search, but
        want to be able to limit results based on items in the Dataset object.
        This function has been renamed and the old name has been mantained for backward compatibility
        The previous names are find_datasets and get_datasets

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

    """
        find a set of datasets according to the simple filter provided
        Original name, kept for for backward compatibility
    """
    get_datasets = datasets_get_many
    find_datasets = datasets_get_many

    def published_data_get_many(self, filter=None) -> List[PublishedData]:
        """
        retrieve all the published data using the simple fiter mechanism. This
        is appropriate when you do not require paging or text search, but
        want to be able to limit results based on items in the Dataset object.
        This function has been renamed and the old name has been maintained for backward compatibility
        The previous name are find_published_data and get_published_data

        For example, a search for published data of a given doi would have
        ```python
        filter = {"doi": "1234"}
        ```

        Parameters
        ----------
        filter : dict
            Dictionary of filtering fields. Must be json serializable.
        """
        if not filter:
            filter = None
        else:
            filter = json.dumps(filter)

        url = f"{self._base_url}PublishedData" + (
            f'?filter={{"where":{filter}}}' if filter else ""
        )
        print(url)
        response = self._send_to_scicat(url, cmd="get")
        if not response.ok:
            err = response.json()["error"]
            logger.error(f'{err["name"]}, {err["statusCode"]}: {err["message"]}')
            return None
        return response.json()

    """
        find a set of published data according to the simple filter provided
        Original name, kept for for backward compatibility
    """
    get_published_data = published_data_get_many
    find_published_data = published_data_get_many

    def datasets_get_one(self, pid=None) -> Dataset:
        """
        Gets dataset with the pid provided.
        This function has been renamed. Provious name has been maintained for backward compatibility.
        Previous names was get_dataset_by_pid

        Parameters
        ----------
        pid : string
            pid of the dataset requested.
        """

        encode_pid = urllib.parse.quote_plus(pid)
        url = f"{self._base_url}/Datasets/{encode_pid}"
        response = self._send_to_scicat(url, cmd="get")
        if not response.ok:
            err = response.json()["error"]
            logger.error(f'{err["name"]}, {err["statusCode"]}: {err["message"]}')
            return None
        return response.json()

    get_dataset_by_pid = datasets_get_one

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

    def instruments_get_one(self, pid: str = None, name: str = None) -> dict:
        """
        Get an instrument by pid or by name.
        If pid is provided it takes priority over name.

        This function has been renamed. Previous name has been maintained for backward compatibility.
        Previous name was get_instrument

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

    get_instrument = instruments_get_one

    def samples_get_one(self, pid: str = None) -> dict:
        """
        Get a sample by pid.
        This function has been renamed. Previous name has been maintained for backward compatibility.
        Previous name was get_sample


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

    get_sample = samples_get_one

    def proposals_get_one(self, pid: str = None) -> dict:
        """
        Get proposal by pid.
        This function has been renamed. Previous name has been maintained for backward compatibility.
        Previous name was get_proposal

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

    get_proposal = proposals_get_one

    def datasets_origdatablocks_get_one(self, pid: str = None) -> dict:
        """
        Get dataset orig datablocks by dataset pid.
        This function has been renamed. Previous name has been maintained for backward compatibility.
        Previous name was get_dataset_origdatablocks

        Parameters
        ----------
        pid : str
            The pid of the dataset

        Returns
        -------
        dict
            The orig_datablocks of the dataset with the requested pid
        """

        encoded_pid = urllib.parse.quote_plus(pid)
        url = f"{self._base_url}/Datasets/{encoded_pid}/origdatablocks"
        response = self._send_to_scicat(url, cmd="get")
        if not response.ok:
            err = response.json()["error"]
            logger.error(f'{err["name"]}, {err["statusCode"]}: {err["message"]}')
            return None
        return response.json()

    get_dataset_origdatablocks = datasets_origdatablocks_get_one

    def datasets_delete(self, pid: str = None) -> dict:
        """
        Delete dataset by pid
        This function has been renamed. Previous name has been maintained for backward compatibility.
        Previous name was delete_dataset

        Parameters
        ----------
        pid : str
            The pid of the dataset to be deleted

        Returns
        -------
        dict
            response from SciCat backend
        """

        encoded_pid = urllib.parse.quote_plus(pid)
        endpoint = "/Datasets/{}".format(encoded_pid)
        url = self._base_url + endpoint
        response = self._send_to_scicat(url, cmd="delete")
        if not response.ok:
            err = response.json()["error"]
            logger.error(f'{err["name"]}, {err["statusCode"]}: {err["message"]}')
            return None
        return response.json()

    delete_dataset = datasets_delete


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
    logger.info(" Getting new token")
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
    return data["id"]  # not sure if semantically correct
