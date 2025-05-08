import nest_asyncio
import pytest
from pydantic import BaseModel
from starfish.common.env_loader import load_env_file
from starfish.data_template.template_gen import data_gen_template
from starfish.data_template.utils.error import DataTemplateValueError, ImportPackageError

nest_asyncio.apply()
load_env_file()


# Define input schema
class TopicGeneratorInput(BaseModel):
    community_name: str
    seed_topics: list[str]
    num_topics: int
    language: str = "en"


# Define output schema
class TopicGeneratorOutput(BaseModel):
    generated_topics: list[str]
    success: bool
    message: str


@pytest.mark.asyncio
async def test_list():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    result = data_gen_template.list()
    assert len(result) != 0


@pytest.mark.asyncio
async def test_list_detail():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    result = data_gen_template.list(is_detail=True)
    assert len(result) != 0


@pytest.mark.asyncio
# @pytest.mark.skip(reason="Skipping this test case as not implementing data_factory decorator outside the function")
async def test_get_datafactory_run():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    data_gen_template.list()
    get_city_info_wf = data_gen_template.get("starfish/get_city_info_wf")
    results = get_city_info_wf.run(
        city_name=["San Francisco", "New York", "Los Angeles"] * 5,
        region_code=["DE", "IT", "US"] * 5,
    )
    assert len(results) == 15


@pytest.mark.asyncio
async def test_get_run_dependencies_not_met():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    data_gen_template.list()
    with pytest.raises(ModuleNotFoundError):
        topic_generator = data_gen_template.get("starfish/math_problem_gen_wf")


@pytest.mark.asyncio
async def test_get_run_dependencies_not_met():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    data_gen_template.list()
    with pytest.raises(ImportPackageError):
        topic_generator = data_gen_template.get("community/topic_generator")


@pytest.mark.asyncio
async def test_get_run_template_Input_Success():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    data_gen_template.list()
    topic_generator_temp = data_gen_template.get("community/topic_generator_success")

    # input_data = TopicGeneratorInput(
    #         community_name="AI Enthusiasts",
    #         seed_topics=["Machine Learning", "Deep Learning"],
    #         num_topics=5
    #     )
    input_data = {"community_name": "AI Enthusiasts", "seed_topics": ["Machine Learning", "Deep Learning"], "num_topics": 1}
    # results = topic_generator_temp.run(input_data.model_dump())
    results = topic_generator_temp.run(input_data)

    assert len(results.generated_topics) == 3


@pytest.mark.asyncio
async def test_get_run_template_Input_Schema_Not_Match():
    """Test with input data and broadcast variables
    - Input: List of dicts with city names
    - Broadcast: num_records_per_city
    - Expected: All cities processed successfully
    """
    with pytest.raises(DataTemplateValueError) as exc_info:
        topic_generator = data_gen_template.get("community/topic_generator_success_1")

        input_data = TopicGeneratorInput(
            community_name="AI Enthusiasts",
        )
        topic_generator.run(input_data)

    # Assert the error message
    assert "Template community/topic_generator_success_1 not found" in str(exc_info.value)
