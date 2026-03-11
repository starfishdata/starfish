from typing import Any, Dict, List

from starfish.data_factory_v2.constants import (
    IDX,
    RECORD_STATUS,
    STATUS_COMPLETED,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
)


class OutputCollector:
    """Collects and caches task output, providing filtered access.

    Replaces the direct queue._queue access pattern with a clean results list.
    """

    def __init__(self):
        self._results: List[Dict[str, Any]] = []
        self._cache: Dict[str, Dict[str, list]] = {}

    def add(self, result: Dict[str, Any]) -> None:
        """Add a task result. Invalidates cache."""
        self._results.append(result)
        self._cache.clear()

    def _build_cache(self) -> None:
        """Build filtered cache from all results."""
        if self._cache:
            return

        self._cache = {
            STATUS_COMPLETED: {"result": [], IDX: []},
            STATUS_DUPLICATE: {"result": [], IDX: []},
            STATUS_FAILED: {"result": [], IDX: []},
            STATUS_FILTERED: {"result": [], IDX: []},
        }

        for record in self._results:
            idx = record.get(IDX)
            status = record.get(RECORD_STATUS)
            if status not in self._cache:
                continue

            if status == STATUS_FAILED:
                output = record.get("err", [])
            else:
                output = record.get("output", [])

            self._cache[status][IDX].extend([idx] * len(output))
            self._cache[status]["result"].extend(output)

    def get_output(self, status: str = STATUS_COMPLETED) -> List[Any]:
        """Get output data filtered by status."""
        self._build_cache()
        return self._cache.get(status, {}).get("result", [])

    def get_indices(self, status: str = STATUS_COMPLETED) -> List[int]:
        """Get record indices filtered by status."""
        self._build_cache()
        return self._cache.get(status, {}).get(IDX, [])

    @property
    def results(self) -> List[Dict[str, Any]]:
        return self._results

    def __len__(self) -> int:
        return len(self._results)
