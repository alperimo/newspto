from typing import Union

import datasets

type Dataset = Union[datasets.DatasetDict, datasets.IterableDataset, datasets.IterableDatasetDict, datasets.Dataset]