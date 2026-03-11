from asyncio import Queue, QueueFull
from copy import deepcopy
from inspect import Parameter, signature
from typing import Any, Callable, Dict, List, Tuple

from starfish.data_factory_v2.constants import IDX
from starfish.data_factory_v2.errors import InputError


def convert_input(data: List[Dict[str, Any]] = None, **kwargs) -> Tuple[Queue, List[Dict[str, Any]]]:
    """Convert user input into a queue of records for processing.

    Handles three input patterns:
    - data: List of dicts, each becoming a record
    - Parallel kwargs: lists/tuples zipped together
    - Broadcast kwargs: scalar values added to all records

    Returns:
        (queue, original_records) - the queue for processing and a deepcopy for reference
    """
    if data is None:
        data = []

    # Separate parallel sources (lists) from broadcast values (scalars)
    parallel_sources = {}
    broadcast_kwargs = {}

    if isinstance(data, list) and len(data) > 0:
        parallel_sources["data"] = data

    for key, value in kwargs.items():
        if isinstance(value, (list, tuple)):
            parallel_sources[key] = value
        else:
            broadcast_kwargs[key] = value

    # Validate parallel sources have same length
    lengths = [len(v) for v in parallel_sources.values()]
    if len(set(lengths)) > 1:
        raise InputError("All parallel sources must have the same length")

    batch_size = lengths[0] if lengths else 1
    queue = Queue()
    records = []

    for i in range(batch_size):
        record = {IDX: i}

        if "data" in parallel_sources:
            record.update(parallel_sources["data"][i])

        for key in parallel_sources:
            if key != "data":
                record[key] = parallel_sources[key][i]

        record.update(broadcast_kwargs)
        records.append(record)

    for record in records:
        try:
            queue.put_nowait(record)
        except QueueFull:
            raise InputError("Queue is full - cannot add more items")

    return queue, deepcopy(records)


def validate_params(func: Callable, sample_record: Dict[str, Any]) -> None:
    """Validate that input record keys match the function signature.

    Raises InputError if there's a mismatch.
    """
    func_sig = signature(func)

    for param_name, param in func_sig.parameters.items():
        if param.default is not Parameter.empty:
            continue
        if param_name not in sample_record:
            raise InputError(
                f"Record is missing required parameter '{param_name}' "
                f"for function {func.__name__}"
            )

    for key in sample_record:
        if key != IDX and key not in func_sig.parameters:
            raise InputError(
                f"Record contains unexpected parameter '{key}' "
                f"not found in function {func.__name__}"
            )
