import pandas as pd
import asyncio
from groq import Groq
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import httpx
from pathlib import Path
from RAG import RAG
from Environment import Environment

env = Environment()


async def get_properties_at_cambridge_bay():
    """Get a list of properties of data available at Cambridge Bay
    Returns a list of dictionaries turned into a string.
    Each Item in the list includes:
    - description (str): Description of the property. The description may have a colon in it.
    - propertyCode (str): Property Code of the property
    example: '{"Description of the property": Property Code of the property}'
    """
    property_API = (
        f"https://data.oceannetworks.ca/api/properties?locationCode={CAMBRIDGE_LOCATION_CODE}&token={ONC_TOKEN}"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(property_API)
        response.raise_for_status()  # Error handling

        # Convert from JSON to Python dictionary for cleanup, return as JSON string
        raw_data = response.json()
        list_of_dicts = [
            {"description": item["description"], "propertyCode": item["propertyCode"]} for item in raw_data
        ]
        return json.dumps(list_of_dicts)


async def get_daily_sea_temperature_stats_cambridge_bay(day_str: str):
    """
    Get daily sea temperature statistics for Cambridge Bay
    Args:
        day_str (str): Date in YYYY-MM-DD format
    """
    # Parse into datetime object to add 1 day (accounts for 24-hour period)
    date_to = datetime.strptime(day_str, "%Y-%m-%d") + timedelta(days=1)
    date_to_str: str = date_to.strftime("%Y-%m-%d")  # Convert back to string

    async with httpx.AsyncClient() as client:
        # Get the data from ONC API
        temp_api = f"https://data.oceannetworks.ca/api/scalardata/location?locationCode={CAMBRIDGE_LOCATION_CODE}&deviceCategoryCode=CTD&propertyCode=seawatertemperature&dateFrom={day_str}&dateTo={date_to_str}&rowLimit=80000&outputFormat=Object&resamplePeriod=86400&token={ONC_TOKEN}"
        response = await client.get(temp_api)
        response.raise_for_status()  # Error handling
        response = response.json()

    if response["sensorData"] is None:
        return ""
        return json.dumps({"result": "No data available for the given date."})

    data = response["sensorData"][0]["data"][0]

    # Get min, max, and average and store in dictionary
    return json.dumps(
        {
            "daily_min": round(data["minimum"], 2),
            "daily_max": round(data["maximum"], 2),
            "daily_avg": round(data["value"], 2),
        }
    )


async def run_conversation(user_prompt, RAG_instance: RAG):
    # Initialize the conversation with system and user messages
    CurrentDate = datetime.now().strftime("%Y-%m-%d")
    messages = [
        {
            "role": "system",
            "content": f"You are an assistant for Oceans Network Canada that helps users access ONCs database via natural language.  \
            You can choose to use the given tools to obtain the data needed to answer the prompt and provide the results if that is required. Dont provide the results in JSON format. Make it readable! \
            The current day is: {CurrentDate}.",
        },
        {
            "role": "user",
            "content": user_prompt,
        },
        {"role": "system", "content": ""},  # Where Data retrieval from Vector DB will occur and be stored
    ]
    # Define the available tools (i.e. functions) for our model to use
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_properties_at_cambridge_bay",
                "description": "Get a list of properties of data available at Cambridge Bay. The function returns a list of dictionaries. Each Item in the list includes:\n        - description (str): Description of the property. The description may have a colon in it.\n        - propertyCode (str): Property Code of the property\n",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_daily_sea_temperature_stats_cambridge_bay",
                "description": "Get daily sea temperature statistics for Cambridge Bay\nArgs:\n    day_str (str): Date in YYYY-MM-DD format",
                "parameters": {
                    "properties": {
                        "day_str": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format for when daily sea temperature is wanted for",
                        }
                    },
                    "required": ["day_str"],
                    "type": "object",
                },
            },
        },
    ]
    # print("Tools defined successfully.")
    vectorDBResponse = RAG_instance.get_documents(user_prompt)
    messages[2] = {"role": "system", "content": vectorDBResponse.to_string()}
    # Make the initial API call to Groq
    response = env.get_client().chat.completions.create(
        model=env.get_model(),  # LLM to use
        messages=messages,  # Conversation history
        stream=False,
        tools=tools,  # Available tools (i.e. functions) for our LLM to use
        tool_choice="auto",  # Let our LLM decide when to use tools
        max_completion_tokens=4096,  # Maximum number of tokens to allow in our response
        temperature=0.5,  # A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
    )
    # Extract the response and any tool call responses
    response_message = response.choices[0].message
    # print("Response received from Groq API.")
    # print("Response message:", response_message)
    tool_calls = response_message.tool_calls
    if tool_calls:
        # Define the available tools that can be called by the LLM
        available_functions = {
            "get_properties_at_cambridge_bay": get_properties_at_cambridge_bay,
            "get_daily_sea_temperature_stats_cambridge_bay": get_daily_sea_temperature_stats_cambridge_bay,
        }
        # Add the LLM's response to the conversation
        messages.append(response_message)

        # Process each tool call
        # print("Processing tool calls...")
        # print("Tool calls:", tool_calls)
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            # Call the tool and get the response
            function_response = await function_to_call(**function_args)
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",  # Indicates this message is from tool use
                    "name": function_name,
                    "content": function_response,
                }
            )
        # Make a second API call with the updated conversation
        second_response = env.get_client.chat.completions.create(
            model=env.get_model,
            messages=messages,
            stream=False,
            tools=tools,
            tool_choice="auto",
            max_completion_tokens=4096,
            temperature=0.5,
        )  # Calls LLM again with all the data from all functions
        # Return the final response
        # print("Second response received from Groq API.")
        # print("Second response message:", second_response.choices)
        return second_response.choices[0].message.content
    else:
        return response_message.content


async def main():

    RAG_instance = RAG()
    print("RAG instance created successfully.")
    user_prompt = "what properties are available at Cambridge Bay?"
    while user_prompt not in ["", "exit"]:
        response = await run_conversation(user_prompt, RAG_instance)
        print(response)
        user_prompt = input("Enter your next question (or 'exit' to quit): ")
    # user_prompt = "what is the temp at cambridge bay?"
    # prompt = LLMPrompt(user_prompt)
    # response = await run_conversation(user_prompt, RAG_instance)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
