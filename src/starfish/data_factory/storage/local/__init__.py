"""Local storage implementation for the StarFish storage layer.
This implementation uses SQLite for metadata and local JSON files for data.
"""

from starfish.data_factory.storage.base import register_storage
from starfish.data_factory.storage.local.local_storage import LocalStorage

# Register the LocalStorage implementation with the file:// scheme
register_storage("local", factory_func=lambda config: LocalStorage(config.storage_uri, getattr(config, "data_storage_uri_override", None)))
