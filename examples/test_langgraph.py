import asyncio
from typing import Dict, List, TypedDict, Annotated, Sequence
from datetime import datetime

from langgraph.graph import Graph, StateGraph
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool

from starfish import StructuredLLM, data_factory
from starfish.data_factory.constants import RECORD_STATUS
from starfish.data_factory.enums import RecordStatus

# Define a simple tool
@tool
def get_weather(location: str) -> str:
    """Get the weather for a location."""
    # Mock implementation
    return f"The weather in {location} is sunny with a temperature of 72°F."

# Define a simple tool
@tool
def get_population(city: str) -> str:
    """Get the population of a city."""
    # Mock implementation
    populations = {
        "New York": "8.8 million",
        "Los Angeles": "4 million",
        "Chicago": "2.7 million",
        "Houston": "2.3 million",
        "Miami": "450,000"
    }
    return f"The population of {city} is {populations.get(city, 'unknown')}."

# Define the state type
class AgentState(TypedDict):
    messages: Annotated[Sequence[HumanMessage | AIMessage], "The messages in the conversation"]
    next: Annotated[str, "The next node to run"]

# Create a simple agent that uses tools
def create_agent():
    # Define the agent function
    def agent(state: AgentState) -> AgentState:
        messages = state["messages"]
        
        # Get the last message
        last_message = messages[-1]
        
        # If it's a human message, process it
        if isinstance(last_message, HumanMessage):
            # Extract the query type and city name
            content = last_message.content.lower()
            city_name = None
            
            if "weather" in content:
                # Extract the city name
                city_name = content.split("weather in ")[-1].rstrip("?").strip()
                # Get the weather
                weather = get_weather(city_name)
                # Add the response to the messages
                messages.append(AIMessage(content=weather))
                # Set the next node to output
                return {"messages": messages, "next": "output"}
            
            elif "population" in content:
                # Extract the city name
                city_name = content.split("population in ")[-1].rstrip("?").strip()
                # Get the population
                population = get_population(city_name)
                # Add the response to the messages
                messages.append(AIMessage(content=population))
                # Set the next node to output
                return {"messages": messages, "next": "output"}
            
            # If no specific request, use the LLM to generate a response
            else:
                # Create a simple LLM response
                response = f"I received your message: {last_message.content}. How can I help you with weather or population information?"
                # Add the response to the messages
                messages.append(AIMessage(content=response))
                # Set the next node to output
                return {"messages": messages, "next": "output"}
        
        # If it's not a human message, just end
        return {"messages": messages, "next": "output"}
    
    # Define the output function
    def output(state: AgentState) -> AgentState:
        # Just return the state as is
        return state
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add the nodes
    workflow.add_node("agent", agent)
    workflow.add_node("output", output)
    
    # Set the entry point
    workflow.set_entry_point("agent")
    
    # Add edges
    workflow.add_edge("agent", "output")
    
    # Set the output node
    workflow.set_finish_point("output")
    
    # Compile the graph
    app = workflow.compile()
    
    return app

# Create a function that uses the LangGraph app
async def process_city_query(city_name: str, query_type: str = "weather"):
    # Create the agent
    agent = create_agent()
    
    # Create the initial state
    initial_state = {
        "messages": [HumanMessage(content=f"What's the {query_type} in {city_name}?")],
        "next": "agent"
    }
    
    # Run the agent
    result = agent.invoke(initial_state)
    
    # Return the last message content
    return {RECORD_STATUS: RecordStatus.COMPLETED, "output_ref": result["messages"][-1].content}

# Wrap the function with the data factory decorator
@data_factory(max_concurrency=5)
async def process_cities(city_name, query_type="weather"):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} - Processing {city_name} for {query_type}")
    return await process_city_query(city_name, query_type)

# Test the function
if __name__ == "__main__":
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} - Starting test with max_concurrency=5")
    
    # Run the function with multiple cities
    results = process_cities.run(data=[
        {'city_name': 'New York', 'query_type': 'weather'},
        {'city_name': 'Los Angeles', 'query_type': 'weather'},
        {'city_name': 'Chicago', 'query_type': 'population'},
        {'city_name': 'Houston', 'query_type': 'population'},
        {'city_name': 'Miami', 'query_type': 'weather'}
    ])
    
    # Print the results
    for i, result in enumerate(results):
        print(f"Result {i+1}: {result}")
    
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} - Finished test") 