from datetime import datetime
import enum
import base64
import hashlib
import logging
import json
import re
from typing import Optional
from urllib.parse import urljoin, quote_plus

from pydantic import BaseModel
import requests

from deprecation import deprecated

from pyscicat.model import (
    Attachment,
    Datablock,
    Dataset,
    DerivedDataset,
    Instrument,
    OrigDatablock,
    Proposal,
    RawDataset,
    Sample,
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
        base_url: str,
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

        if not self._token:
            assert (self._username is not None) and (
                self._password is not None
            ), "SciCat login credentials (username, password) must be provided if token is not provided"
            self._token = get_token(self._base_url, self._username, self._password)
            self._headers["Authorization"] = "Bearer {}".format(self._token)


    def _send_to_scicat(
        self, 
        cmd: str, 
        endpoint: str, 
        data: BaseModel = None,
        exclude_fields: set = {},
    ):
        """sends a command to the SciCat API server using url and token, returns the response JSON
        Get token with the getToken method"""
        if type(data) == dict:
            return requests.request(
                method=cmd,
                url=urljoin(self._base_url, endpoint),
                json=data if data is not None else None,
                params={"access_token": self._token},
                headers=self._headers,
                timeout=self._timeout_seconds,
                stream=False,
                verify=True,
            )

        else:

            return requests.request(
                method=cmd,
                url=urljoin(self._base_url, endpoint),
                json=data.dict(exclude=exclude_fields,exclude_none=True,exclude_unset=True) if data is not None else None,
                params={"access_token": self._token},
                headers=self._headers,
                timeout=self._timeout_seconds,
                stream=False,
                verify=True,
            )


    def _call_endpoint(
        self,
        cmd: str,
        endpoint: str,
        data: BaseModel = None,
        operation: str = "",
        allow_404=False,
        exclude_fields: set = {},
    ) -> Optional[dict]:
        response = self._send_to_scicat(cmd=cmd, endpoint=endpoint, data=data, exclude_fields=exclude_fields)
        result = response.json()
        if not response.ok:
            err = result.get("error", {})
            if (
                allow_404
                and response.status_code == 404
                and re.match(r"Unknown (.+ )?id", err.get("message", ""))

            ):
                # The operation failed but because the object does not exist in SciCat.
                logger.error("Error in operation %s: %s", operation, err)
                return None
            raise ScicatCommError(f"Error in operation {operation}: {err}")
        logger.info(
            "Operation '%s' successful%s",
            operation,
            f"pid={result['pid']}" if "pid" in result else "",
        )
        return result

    @deprecated(deprecated_in='1.0.0', details='this method no longer works with the new Scicat '
                                        'backend, which does not have a method to '
                                        'replaceOrCreate dataset. update_dataset or '
                                        'upload_dataset should be used'
                )
    def datasets_replace(self, dataset: Dataset) -> str:
        """
        Create a new dataset or update an existing one
        This function was renamed.
        It is still accessible with the original name for backward compatibility
        The original names were upload_dataset replace_datasets
        This function is obsoleteand it will be remove in next relesases


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
            dataset_url = "RawDataSets/replaceOrCreate"
        elif isinstance(dataset, DerivedDataset):
            dataset_url = "DerivedDatasets/replaceOrCreate"
        else:
            raise TypeError(
                "Dataset type not recognized (not Derived or Raw dataset instances)"
            )
        return self._call_endpoint(
            cmd="post", endpoint=dataset_url, data=dataset, operation="datasets_replace"
        )

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
        str
            pid of the dataset

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """
        return self._call_endpoint(
            cmd="post", 
            endpoint="Datasets", 
            data=dataset, 
            operation="datasets_create",
            exclude_fields={'pid'},
        )

    """
        Upload a new dataset
        Original name, kept for for backward compatibility
    """
    upload_new_dataset = datasets_create
    create_dataset = datasets_create

    @deprecated(deprecated_in='1.0.0', details='this method no longer works with the new'
                                        ' Scicat backend, which only has'
                                        ' one end point for Datasets and does not'
                                        ' retain separate RawDataset and'
                                        ' DerivedDatasetEndpoints. update_dataset'
                                        'or upload_dataset should be used')
    def datasets_raw_replace(self, dataset: Dataset) -> str:
        """
        Create a new raw dataset or update an existing one
        This function was renamed.
        It is still accessible with the original name for backward compatibility
        The original names were repalce_raw_dataset and upload_raw_dataset
        This function is obsolete and it will be removed in future releases

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
        return self._call_endpoint(
            cmd="post",
            endpoint="RawDataSets/replaceOrCreate",
            data=dataset,
            operation="datasets_raw_replace",
        )

    """
        Upload a raw dataset
        Original name, kept for for backward compatibility
    """
    upload_raw_dataset = datasets_raw_replace
    replace_raw_dataset = datasets_raw_replace

    @deprecated(deprecated_in='1.0.0', details='this method no longer works with the new Scicat '
                                        'backend,which only has one end point for '
                                        'Datasets and does not retain separate RawDataset'
                                        ' and DerivedDatasetEndpoints.'
                                        'update_datsets or  upload_dataset should be used')
    def datasets_derived_replace(self, dataset: Dataset) -> str:
        """
        Create a new derived dataset or update an existing one. This function was renamed.
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
        return self._call_endpoint(
            cmd="post",
            endpoint="DerivedDataSets/replaceOrCreate",
            data=dataset,
            operation="datasets_derived_replace",
        )

    def datasets_update(self, dataset: Dataset, pid: str) -> str:
        """Updates an existing dataset
        This function was renamed.
        It is still accessible with the original name for backward compatibility
        The original name was update_dataset.

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
        return self._call_endpoint(
            cmd="patch",
            endpoint=f"Datasets/{quote_plus(pid)}",
            data=dataset,
            operation="datasets_update",
        )

    """
        Update a dataset
        Original name, kept for for backward compatibility
    """
    update_dataset = datasets_update

    @deprecated(deprecated_in='1.0.0', details='this method no longer works with the new Scicat backend,'
                                        ' function datasets_origdatablock should be used.')
    def datasets_datablock_create(
        self, datablock: Datablock, datasetType: str = "RawDatasets"
    ) -> dict:
        """
        Create a new datablock for a dataset.
        The dataset can be both Raw or Derived.
        It is still accessible with the original name for backward compatibility
        The original names were create_dataset_datablock and upload_datablock
        This function is obsolete and will be removed in future releases
        Function datasets_datablock_create should be used.

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
        endpoint = f"{datasetType}/{quote_plus(datablock.datasetId)}/origdatablocks"
        return self._call_endpoint(
            cmd="post",
            endpoint=endpoint,
            data=datablock,
            operation="datasets_datablock_create",
        )

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
        endpoint = f"Datasets/{quote_plus(origdatablock.datasetId)}/origdatablocks"
        return self._call_endpoint(
            cmd="post",
            endpoint=endpoint,
            data=origdatablock,
            operation="datasets_origdatablock_create",
            exclude_fields={'id','datasetId','ownerGroup','accessGroups'},
        )

    """
        Create a new SciCat Dataset OrigDatablock
        Original name, kept for for backward compatibility
    """
    upload_dataset_origdatablock = datasets_origdatablock_create
    create_dataset_origdatablock = datasets_origdatablock_create

    def datasets_attachment_create(
        self, attachment: Attachment, datasetType: str = "RawDatasets"
    ) -> dict:
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
        endpoint = f"{datasetType}/{quote_plus(attachment.datasetId)}/attachments"
        return self._call_endpoint(
            cmd="post",
            endpoint=endpoint,
            data=attachment,
            operation="datasets_attachment_create",
        )

    """
        Create a new attachement for a dataset
        Original name, kept for for backward compatibility
    """
    upload_attachment = datasets_attachment_create
    create_dataset_attachment = datasets_attachment_create

    def samples_create(self, sample: Sample) -> str:
        """
        Create a new sample.
        An error is raised when a sample with the same sampleId already exists.
        This function is also accessible as upload_sample.


        Parameters
        ----------
        sample : Sample
            Sample to upload

        Returns
        -------
        str
            ID of the newly created sample

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """
        return self._call_endpoint(
            cmd="post",
            endpoint="Samples",
            data=sample,
            operation="samples_create",
        )

    upload_sample = samples_create

    def samples_update(self, sample: Sample, sampleId: str = None) -> str:
        """Updates an existing sample

        Parameters
        ----------
        sample : Sample
            Sample to update

        sampleId
            ID of sample being updated. By default, ID is taken from sample parameter.

        Returns
        -------
        str
            ID of the sample

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned

        AssertionError
            Raises if no ID is provided
        """
        if sampleId is None:
            assert sample.sampleId is not None, "sampleId should not be None"
            sampleId = sample.sampleId
        sample.sampleId = None
        return self._call_endpoint(
            cmd="patch",
            endpoint=f"Samples/{quote_plus(sampleId)}",
            data=sample,
            operation="samples_update",
        )

    def instruments_create(self, instrument: Instrument):
        """
        Create a new instrument.
        Note that in SciCat admin rights are required to upload instruments.
        An error is raised when an instrument with the same pid already exists.
        This function is also accessible as upload_instrument.


        Parameters
        ----------
        instrument : Instrument
            Instrument to upload

        Returns
        -------
        str
            pid (or unique identifier) of the newly created instrument

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """
        return self._call_endpoint(
            cmd="post",
            endpoint="Instruments",
            data=instrument,
            operation="instruments_create",
        )

    upload_instrument = instruments_create

    def instruments_update(self, instrument: Instrument, pid: str = None) -> str:
        """Updates an existing instrument.
        Note that in SciCat admin rights are required to upload instruments.

        Parameters
        ----------
        instrument : Instrument
            Instrument to update

        pid
            pid (or unique identifier) of instrument being updated.
            By default, pid is taken from instrument parameter.

        Returns
        -------
        str
            ID of the instrument

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned

        AssertionError
            Raises if no ID is provided
        """
        if pid is None:
            assert instrument.pid is not None, "pid should not be None"
            pid = instrument.pid
        instrument.pid = None
        return self._call_endpoint(
            cmd="patch",
            endpoint=f"Instruments/{quote_plus(pid)}",
            data=instrument,
            operation="instruments_update",
        )

    def proposals_create(self, proposal: Proposal):
        """
        Create a new proposal.
        Note that in SciCat admin rights are required to upload proposals.
        An error is raised when a proposal with the same proposalId already exists.
        This function is also accessible as upload_proposal.


        Parameters
        ----------
        proposal : Proposal
            Proposal to upload

        Returns
        -------
        str
            ID of the newly created proposal

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned
        """
        return self._call_endpoint(
            cmd="post",
            endpoint="Proposals",
            data=proposal,
            operation="proposals_create",
        )

    upload_proposal = proposals_create

    def proposals_update(self, proposal: Proposal, proposalId: str = None) -> str:
        """Updates an existing proposal.
        Note that in SciCat admin rights are required to upload proposals.

        Parameters
        ----------
        proposal : Proposal
            Proposal to update

        proposalId
            ID of proposal being updated. By default, this is taken from proposal parameter.

        Returns
        -------
        str
            ID of the proposal

        Raises
        ------
        ScicatCommError
            Raises if a non-20x message is returned

        AssertionError
            Raises if no ID is provided
        """
        if proposalId is None:
            assert proposal.proposalId is not None, "proposalId should not be None"
            proposalId = proposal.proposalId
        proposal.proposalId = None
        return self._call_endpoint(
            cmd="patch",
            endpoint=f"Proposals/{quote_plus(proposalId)}",
            data=proposal,
            operation="proposals_update",
        )

    def datasets_find(
        self, skip: int = 0, limit: int = 25, query_fields: Optional[dict] = None
    ) -> Optional[dict]:
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

        return self._call_endpoint(
            cmd="get",
            endpoint=f"Datasets/fullquery?{query}",
            operation="datasets_find",
            allow_404=True,
        )

    """
        find a set of datasets according the full query provided
        Original name, kept for for backward compatibility
    """
    get_datasets_full_query = datasets_find
    find_datasets_full_query = datasets_find

    def datasets_get_many(self, filter_fields: Optional[dict] = None) -> Optional[dict]:
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
        If you want to search on partial strings, you can use "like":
        ```python
        filterField = {"proposalId": {"like":"123"}}
        ```

        Parameters
        ----------
        filter_fields : dict
            Dictionary of filtering fields. Must be json serializable.
        """
        if not filter_fields:
            filter_fields = {}
        filter_fields = json.dumps(filter_fields)
        endpoint = f'/Datasets/?filter={{"where":{filter_fields}}}'
        return self._call_endpoint(
            cmd="get", endpoint=endpoint, operation="datasets_get_many", allow_404=True
        )

    """
        find a set of datasets according to the simple filter provided
        Original name, kept for for backward compatibility
    """
    get_datasets = datasets_get_many
    find_datasets = datasets_get_many

    def published_data_get_many(self, filter=None) -> Optional[dict]:
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
        if filter:
            filter = json.dumps(filter)

        endpoint = "PublishedData" + (f'?filter={{"where":{filter}}}' if filter else "")
        return self._call_endpoint(
            cmd="get",
            endpoint=endpoint,
            operation="published_data_get_many",
            allow_404=True,
        )

    """
        find a set of published data according to the simple filter provided
        Original name, kept for for backward compatibility
    """
    get_published_data = published_data_get_many
    find_published_data = published_data_get_many

    def datasets_get_one(self, pid: str) -> Optional[dict]:
        """
        Gets dataset with the pid provided.
        This function has been renamed. Provious name has been maintained for backward compatibility.
        Previous names was get_dataset_by_pid

        Parameters
        ----------
        pid : string
            pid of the dataset requested.
        """
        return self._call_endpoint(
            cmd="get",
            endpoint=f"Datasets/{quote_plus(pid)}",
            operation="datasets_get_one",
            allow_404=True,
        )

    get_dataset_by_pid = datasets_get_one

    def instruments_get_one(self, pid: str = None, name: str = None) -> Optional[dict]:
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
            endpoint = f"Instruments/{quote_plus(pid)}"
        elif name:
            query = json.dumps({"where": {"name": {"like": name}}})
            endpoint = f"Instruments/findOne?{query}"
        else:
            raise ValueError("You must specify instrument pid or name")

        return self._call_endpoint(
            cmd="get",
            endpoint=endpoint,
            operation="instruments_get_one",
            allow_404=True,
        )

    get_instrument = instruments_get_one

    def samples_get_one(self, pid: str) -> Optional[dict]:
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
        return self._call_endpoint(
            cmd="get",
            endpoint=f"Samples/{quote_plus(pid)}",
            operation="samples_get_one",
            allow_404=True,
        )

    get_sample = samples_get_one

    def proposals_get_one(self, pid: str = None) -> Optional[dict]:
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
        return self._call_endpoint(
            cmd="get", endpoint=f"Proposals/{quote_plus(pid)}", allow_404=True
        )

    get_proposal = proposals_get_one

    def datasets_origdatablocks_get_one(self, pid: str) -> Optional[dict]:
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
        return self._call_endpoint(
            cmd="get",
            endpoint=f"/Datasets/{quote_plus(pid)}/origdatablocks",
            operation="datasets_origdatablocks_get_one",
            allow_404=True,
        )

    get_dataset_origdatablocks = datasets_origdatablocks_get_one

    def datasets_delete(self, pid: str) -> Optional[dict]:
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
        return self._call_endpoint(
            cmd="delete",
            endpoint=f"/Datasets/{quote_plus(pid)}",
            operation="datasets_delete",
            allow_404=True,
        )

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


def _log_in_via_users_login(base_url, username, password):
    response = requests.post(
        urljoin(base_url, "auth/login"),
        json={"username": username, "password": password},
        stream=False,
        verify=True,
    )
    if not response.ok:
        logger.info(f" Failed to log in via endpoint auth/login: {response.json()}")
    return response


def _log_in_via_auth_msad(base_url, username, password):
    import re

    # Strip the api/vn suffix
    base_url = re.sub(r"/api/v\d+/?", "", base_url)
    response = requests.post(
        urljoin(base_url, "auth/msad"),
        json={"username": username, "password": password},
        stream=False,
        verify=True,
    )
    if not response.ok:
        err = response.json()["error"]
        logger.error(
            f'Error retrieving token for user: {err["name"]}, {err["statusCode"]}: {err["message"]}'
        )
        raise ScicatLoginError(response.content)


def get_token(base_url, username, password):
    """logs in using the provided username / password combination
    and receives token for further communication use"""
    # Users/login only works for functional accounts and auth/msad for regular users.
    # Try both and see what works. This is not nice but seems to be the only
    # feasible solution right now.
    logger.info(" Getting new token")

    response = _log_in_via_users_login(base_url, username, password)
    if response.ok:
        return response.json()["id"]  # not sure if semantically correct

    # response = _log_in_via_auth_msad(base_url, username, password)
    # if response.ok:
    #     return response.json()["access_token"]

    err = response.json()["error"]
    logger.error(
        f' Failed log in:  {err["name"]}, {err["statusCode"]}: {err["message"]}'
    )
    raise ScicatLoginError(response.content)
