from fastapi import APIRouter, HTTPException

from starfish.common.logger import get_logger
from starfish import StructuredLLM, data_factory
from web.api.storage import save_dataset, list_datasets_from_storage, get_dataset_from_storage

logger = get_logger(__name__)

router = APIRouter(prefix="/dataset", tags=["dataset"])


@data_factory()
async def default_eval(input_data):
    if not isinstance(input_data, str):
        input_data = input_data

    eval_llm = StructuredLLM(
        prompt="Given input data {{input_data}} please give it score from 1 to 10",
        output_schema=[{"name": "quality_score", "type": "int"}],
        model_name="gpt-4o-mini",
    )

    eval_response = await eval_llm.run(input_data=input_data)
    return eval_response.data


@router.post("/evaluate")
async def evaluate_dataset(request: dict):
    """
    Evaluate a dataset with the given inputs.

    This endpoint evaluates a dataset with the given inputs and returns the output.

    Returns:
        The result of evaluating the dataset
    """
    try:
        # logger.info(f"Evaluating dataset: {request}")
        result = request["evaluatedData"]
        input_data = []
        for item in result:
            input_data.append(str(item))
        processed_data = default_eval.run(input_data=input_data)
        processed_data_index = default_eval.get_index_completed()
        for i in range(len(processed_data_index)):
            result[processed_data_index[i]]["quality_score"] = processed_data[i]["quality_score"]

        # for item in result:
        #     item["quality_score"] = 6
        return result

    except Exception as e:
        logger.error(f"Error evaluating dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error evaluating dataset: {str(e)}")


@router.post("/save")
async def save_dataset_api(request: dict):
    """
    Save a dataset with the given inputs.

    This endpoint saves a dataset with the given inputs and returns the output.
    """
    try:
        # logger.info(f"Saving dataset: {request}")
        await save_dataset(request["projectId"], request["datasetName"], request["data"])
        return request
    except Exception as e:
        logger.error(f"Error saving dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving dataset: {str(e)}")


@router.post("/list")
async def list_datasets(request: dict):
    """
    List all datasets for a given project.
    """
    try:
        datasets = await list_datasets_from_storage(request["projectId"], request["datasetType"])
        return datasets
    except Exception as e:
        logger.error(f"Error listing datasets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing datasets: {str(e)}")


@router.post("/get")
async def get_dataset(request: dict):
    """
    Get a dataset with the given inputs.
    """
    try:
        dataset = await get_dataset_from_storage(request["projectId"], request["datasetName"])
        return dataset
    except Exception as e:
        logger.error(f"Error getting dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting dataset: {str(e)}")
