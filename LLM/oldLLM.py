import pandas as pd
import asyncio
import json
from datetime import datetime
from toolsSprint1 import (
    get_properties_at_cambridge_bay,
    get_daily_sea_temperature_stats_cambridge_bay,
    get_deployed_devices_over_time_interval,
)
from RAG import RAG
from Environment import Environment
from Constants.toolDescriptions import toolDescriptions


class LLM:
    def __init__(
        self, env: Environment, RAG_instance: RAG = None, chatHistory: list[dict] = None, startingPrompt: str = None
    ):
        self.env = env
        self.currentDate = datetime.now().strftime("%Y-%m-%d")

        self.maxChatHistoryLength = 10  # Maximum number of messages to keep in the conversation history
        self.chatHistory = chatHistory if chatHistory is not None else []

        if startingPrompt is None:
            self.startingPrompt = f"You are an assistant for Oceans Network Canada that helps users access ONCs database via natural language. \
                You can choose to use the given tools to obtain the data needed to answer the prompt and provide the results if that is required. Dont provide the results in JSON format. Make it readable! \
                The current day is: {self.currentDate}. Always give a response!"
        else:
            self.startingPrompt = startingPrompt
        self.messages = [
            {
                "role": "system",
                "content": self.startingPrompt,
            },
            {
                "role": "user",
                "content": "",  # Placeholder for user input
            }
        ]

        self.messages = self.chatHistory.copy()  # Adding old messages to the conversation history. Maybe they wanted to start from an old conversation.
        self.__KeepMessagesWithinLimit__()  # Ensuring not over message limit at the start (Will also add the starting prompt and user input placeholder)

        self.toolDescriptions = toolDescriptions
        self.RAG_instance = RAG_instance if RAG_instance else RAG(env)  # Use provided RAG instance or create a new one
        self.available_functions = {
            "get_properties_at_cambridge_bay": get_properties_at_cambridge_bay,
            "get_daily_sea_temperature_stats_cambridge_bay": get_daily_sea_temperature_stats_cambridge_bay,
            "get_deployed_devices_over_time_interval": get_deployed_devices_over_time_interval,
        }
        self.mostRecentData = None  # Placeholder for most recent data, if needed
        
    async def run_conversation(self, user_prompt):
        #print("Starting conversation with user prompt:", user_prompt)
        self.messages[-1]["content"] = user_prompt  # -1 as second last in messages
        #print(self.messages)
        response = self.env.get_client().chat.completions.create(
            model=self.env.get_model(),  # LLM to use
            messages=self.messages,  # Conversation history
            stream=False,
            tools=self.toolDescriptions,  # Available tools (i.e. functions) for our LLM to use
            tool_choice="auto",  # Let our LLM decide when to use tools
            max_completion_tokens=512,  # Maximum number of tokens to allow in our response
            temperature=1,  # A temperature of 1=default balance between randomnes and confidence. Less than 1 is less randomness, Greater than is more randomness
        )
        # Extract the response and any tool call responses
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            # Define the available tools that can be called by the LLM
            # Add the LLM's response to the conversation
            self.messages.append(response_message)
            # Process each tool call
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                if (function_name == "vectorDB"):
                    vectorDBResponse = self.RAG_instance.get_documents(user_prompt)
                    print("Vector DB response:", vectorDBResponse.to_string())
                    #print("Vector DB response:", vectorDBResponse)
                    self.messages.append({"role": "system", "content": vectorDBResponse.to_string()})
                    continue  # Skip to next tool call if vectorDB is called
                function_to_call = self.available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                #print(tool_call.function.arguments)
                if not function_args:
                    function_response = await function_to_call()
                else: 
                    function_response = await function_to_call(**function_args)
                self.messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",  # Indicates this message is from tool use
                        "name": function_name,
                        "content": function_response,
                    }
                )  # May be able to use this for getting most recent data if needed.
            # Store the most recent data if needed
            self.mostRecentData = (
                self.messages[-1]["content"] if self.messages else None
            )  # Last place in list of message is data from tools

            # Make a second API call with the updated conversation
            second_response = self.env.get_client().chat.completions.create(
                model=self.env.get_model(),
                messages=self.messages,
                stream=False,
                tools=self.toolDescriptions,
                tool_choice="auto",
                max_completion_tokens=2048,
                temperature=1,
            )  # Calls LLM again with all the data from all functions
            # Return the final response

            #print("Final response from LLM:", second_response.choices[0].message.content)
            self.chatHistory.append(
                {"role": "user", "content": user_prompt}
            )  # Append the final response to the conversation history
            #print(type(second_response.choices[0].message.content))
            self.chatHistory.append(
                {"role": "system", "content": second_response.choices[0].message.content}
            )  # Append the final response to the conversation history
            self.__KeepMessagesWithinLimit__()
            return second_response.choices[0].message.content
        else:
            # print("no tool calls", response_message.content)
            self.chatHistory.append(
                {"role": "user", "content": user_prompt}
            )  # Append the final response to the conversation history
            self.chatHistory.append(
                {"role": "system", "content": response_message.content}
            )  # Append the final response to the conversation history
            self.__KeepMessagesWithinLimit__()
            return response_message.content

    def get_messages(self):
        return self.messages

    def updateCurrentData(self, newDate: str = None):
        self.currentDate = newDate if newDate else datetime.now().strftime("%Y-%m-%d")

    def getMostRecentData(self):
        # Will use this function to get the most recent data to put into a pandas dataframe which can be used for data download as a csv file.
        if self.mostRecentData is None:
            raise ValueError("No most recent data available. Please run a conversation first.")
        # Assuming mostRecentData is a string that can be converted to a DataFrame
        if isinstance(self.mostRecentData, str):
            # Convert string to DataFrame
            data = json.loads(self.mostRecentData)
            return (
                pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            )  # Can use dataframe to save as a CSV
        elif not isinstance(self.mostRecentData, pd.DataFrame):
            raise TypeError("Most recent data is not in a recognized format.")

    def __KeepMessagesWithinLimit__(self):
        # Keep the last maxChatHistoryLength messages in the conversation history
        # Keep only the last maxChatHistoryLength messages[
        self.messages = self.chatHistory[-self.maxChatHistoryLength :] + [
            {
                "role": "system",
                "content": self.startingPrompt,
            },
            {
                "role": "user",
                "content": "",  # Placeholder for user input
            }
        ]

    def clear_chat_history(self):
        # Clear the chat history
        self.chatHistory = []
        self.messages = [
            {
                "role": "system",
                "content": self.startingPrompt,
            },
            {
                "role": "user",
                "content": "",  # Placeholder for user input
            }
        ]


async def main():

    env = Environment()
    RAG_instance = RAG(env)
    print("RAG instance created successfully.")
    try:
        LLM_Instance = LLM(env = env, RAG_instance=RAG_instance)  # Create an instance of the LLM class
        user_prompt = input("Enter your first question (or 'exit' to quit): ")
        while user_prompt not in ["exit", "quit"]:
            response = await LLM_Instance.run_conversation(user_prompt)
            print(response)
            user_prompt = input("Enter your next question (or 'exit' to quit): ")
    except Exception as e:
        print("Error occurred:", e)


if __name__ == "__main__":
    asyncio.run(main())
