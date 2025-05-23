from starfish.data_factory.utils.state import MutableSharedState
from typing import Any


## Helper Functions
def save_value_by_topic(state: MutableSharedState, topic: str, value: Any) -> None:
    """Saves a value indexed by topic in the shared state."""
    # Get current state data
    topic_collections = state.get("topic_data")
    if topic_collections is None:
        topic_collections = {}
    else:
        topic_collections = topic_collections.copy()

    # Initialize topic collection if needed
    with state._lock:
        if topic not in topic_collections or not isinstance(topic_collections[topic], list):
            topic_collections[topic] = []
        # Append the value and update state
        topic_collections[topic].append(value)
    state.set("topic_data", topic_collections)


def fetch_values_by_topic(state: MutableSharedState, topic: str) -> list:
    """Fetches all values indexed by a topic from the shared state."""
    topic_collections = state.get("topic_data")
    if not topic_collections:
        return []

    topic_values = topic_collections.get(topic)
    if not topic_values or not isinstance(topic_values, list):
        return []

    return topic_values.copy()
