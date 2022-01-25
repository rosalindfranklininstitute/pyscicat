import enum
from typing import List, Dict, Optional

from pydantic import BaseModel


class DatasetType(str, enum.Enum):
    """type of Dataset"""

    raw = "raw"
    derived = "derived"


class Ownable(BaseModel):
    """Many objects in SciCat are ownable"""

    ownerGroup: str
    accessGroups: List[str]


class MongoQueryable(BaseModel):
    """Many objects in SciCat are mongo queryable"""

    createdBy: Optional[str]
    updatedBy: Optional[str]
    updatedAt: Optional[str]
    createdAt: Optional[str]


class Dataset(Ownable, MongoQueryable):
    """
    A dataset in SciCat, base class for derived and raw datasets
    """

    pid: Optional[str]
    classification: Optional[str]
    contactEmail: str
    creationLocation: str
    creationTime: str  # datetime
    dataFormat: str
    datasetName: Optional[str]
    description: Optional[str]
    history: Optional[List[dict]] = [{0: "Entry created"}]
    instrumentId: Optional[str]
    isPublished: Optional[bool] = False
    keywords: Optional[List[str]]
    license: Optional[str]
    numberOfFiles: Optional[int]
    numberOfFilesArchived: Optional[int]
    orcidOfOwner: Optional[str]
    packedSize: Optional[int]
    principalInvestigator: str
    owner: str
    ownerEmail: Optional[str]
    sharedWith: Optional[List[str]]
    size: Optional[int]
    sourceFolder: str
    sourceFolderHost: Optional[str]
    techniques: Optional[List[dict]]  # with {'pid':pid, 'name': name} as entries
    type: DatasetType
    validationStatus: Optional[str]
    version: Optional[str]


class RawDataset(Dataset):
    """ Raw datasets from which derived datasets are... derived."""

    principalInvestigator: Optional[str]
    creationLocation: Optional[str]
    type: DatasetType = "raw"
    createdAt: Optional[str]  # datetime
    updatedAt: Optional[str]  # datetime
    dataFormat: Optional[str]
    endTime: Optional[str]  # datetime
    sampleId: Optional[str]
    proposalId: Optional[str]
    scientificMetadata: Optional[Dict]


class DerivedDataset(Dataset):
    """ Derived datasets which have been generated based on one or more raw datasets"""

    investigator: Optional[str]
    inputDatasets: List[str]
    usedSoftware: Optional[str]
    jobParameters: Optional[dict]
    jobLogData: Optional[str]
    scientificMetadata: Optional[Dict]


class DataFile(MongoQueryable):
    """
    A reference to a file in SciCat. Path is relative
    to the Dataset's sourceFolder parameter

    """

    path: str
    size: int
    time: Optional[str]
    uid: Optional[str] = None
    gid: Optional[str] = None
    perm: Optional[str] = None


class Datablock(Ownable):
    """
    A Datablock maps between a Dataset and contains DataFiles
    """

    id: Optional[str]
    # archiveId: str = None  listed in catamel model, but comes back invalid?
    size: int
    packedSize: Optional[int]
    chkAlg: Optional[int]
    version: str = None
    dataFileList: List[DataFile]
    datasetId: str


class Attachment(Ownable):
    """
    Attachments can be any base64 encoded string...thumbnails are attachments
    """

    id: Optional[str]
    thumbnail: str
    caption: Optional[str]
    datasetId: str
