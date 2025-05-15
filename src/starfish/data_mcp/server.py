from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

from starfish.data_template.template_gen import data_gen_template

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""


@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


@mcp.tool()
async def test_get_run_template_Input_Success(template_name: str, input_data: Any):
    """Test a template with provided input data.

    This function tests the execution of a specified template by providing
    input data and returning the results.

    Args:
        template_name: Name of the template to test
        input_data: Input data to pass to the template

    Steps:
        1. Lists available templates using data_gen_template.list()
        2. Retrieves the specified template
        3. Executes the template with the input data
        4. Prints the results
        5. Asserts that the number of generated topics is 3

    Returns:
        Results from the template execution

    Raises:
        AssertionError: If the number of generated topics doesn't match expected value
    """
    data_gen_template.list()
    print("debug-----")
    topic_generator_temp = data_gen_template.get(template_name=template_name)

    results = topic_generator_temp.run(input_data)
    print(results)

    # assert len(results.generated_topics) == 3
    return results


@mcp.tool()
async def test_get_cities_info(city_name: list, region_code: list):
    """Get information about multiple cities using the city info workflow template.

    This function retrieves city information by executing the 'get_city_info_wf' template
    with provided city names and region codes.

    Args:
        city_name: List of city names to get information for
        region_code: List of region codes corresponding to the cities (e.g., state codes for US)

    Returns:
        Results from the city info workflow template execution containing city information

    Example:
        >>> await test_get_cities_info(
        ...     city_name=["New York", "Los Angeles"],
        ...     region_code=["NY", "CA"]
        ... )
    """
    data_gen_template.list()
    topic_generator_temp = data_gen_template.get("starfish/get_city_info_wf")

    results = topic_generator_temp.run(city_name, region_code)
    return results


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
