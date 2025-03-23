from pymongo import MongoClient
from langchain_ollama import ChatOllama
from langchain.agents import initialize_agent, Tool, AgentType
import pandas as pd
import ast
from bson.decimal128 import Decimal128
from typing import List, Dict, Any
from langchain.memory import ConversationSummaryMemory
from langchain.memory.chat_message_histories import ChatMessageHistory
import chainlit as cl

class CustomMemoryManager:
    def __init__(self, llm):
        self.max_history = 5
        self.llm = llm
        self.chat_history = ChatMessageHistory()
        self.memory = ConversationSummaryMemory(
            llm=self.llm,
            chat_memory=self.chat_history,
            return_messages=True
        )
        self.displayed_history: List[Dict[str, Any]] = []
        self.interaction_count = 0
        self.previous_summary = ""

    def add_interaction(self, user_query: str, bot_response: Any) -> None:
        self.chat_history.add_user_message(user_query)
        bot_response_str = str(bot_response) if isinstance(bot_response, pd.DataFrame) else bot_response
        self.chat_history.add_ai_message(bot_response_str)
        
        self.displayed_history.append({
            "user": user_query,
            "bot": bot_response,
            "is_summary": False
        })
        
        self.interaction_count += 1
        
        if self.interaction_count % self.max_history == 0:
            self._create_and_store_summary()

    def _create_and_store_summary(self) -> None:
        # Generate new summary using previous summary as context
        new_summary = self.memory.predict_new_summary(
            messages=self.chat_history.messages,
            existing_summary=self.previous_summary
        )
        
        # Create a unified summary
        if self.previous_summary:
            complete_summary = f"{self.previous_summary} {new_summary}"
        else:
            complete_summary = new_summary

        self.displayed_history.append({
            "user": "Conversation Summary",
            "bot": complete_summary,
            "is_summary": True,
            "summary_at": self.interaction_count
        })
        
        self.previous_summary = complete_summary
        
        # Clear the chat history but maintain context
        self.chat_history.clear()
        self.chat_history.add_user_message(f"Previous conversation context: {complete_summary}")

    def get_history(self) -> List[Dict[str, Any]]:
        return self.displayed_history

# MongoDB Connection
MONGODB_URI = "mongodb+srv://kanipriya2003:Kani03@cluster0.ey4i8.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGODB_URI)

# Initialize Llama instance
ollama = ChatOllama(model="hermes3:8b", base_url="https://ollama-hermes-863607447394.us-central1.run.app/")

def execute_mongodb_query(query, page=0, page_size=60):
    try:
        page_size = min(page_size, 60)
        if isinstance(query, str):
            query = ast.literal_eval(query)
        print(f"Executing query: {query}")
        
        filter_query = query.get("filter", {})
        sort_query = query.get("sort", {})
        projection = query.get("projection", None)
        aggregation_pipeline = query.get("aggregation", [])
        
        print(f"Filter query: {filter_query}, Sort query: {sort_query}")
        
        skip = page * page_size
        limit = page_size
        
        db = client[query['database']]
        collection = db[query['collection']]
        
        if aggregation_pipeline:
            cursor = collection.aggregate(aggregation_pipeline)
        else:
            cursor = collection.find(filter_query, projection)
        
        if sort_query:
            cursor = cursor.sort(sort_query)
        
        results = list(cursor.skip(skip).limit(limit))
        if results:
            for result in results:
                if "_id" in result:
                    result["_id"] = str(result["_id"])
            return results
        return "No data found."
    except Exception as e:
        return f"Error executing query: {str(e)}"

def flatten_result(result):
    flattened_result = []
    for item in result:
        if isinstance(item, dict):
            flattened_item = {
                k: (float(v.to_decimal()) if isinstance(v, Decimal128) else str(v) if isinstance(v, (list, dict)) else v)
                for k, v in item.items()
            }
            flattened_result.append(flattened_item)
    return flattened_result

async def handle_user_query_with_tool(user_query, memory_manager):
    # Check if both database and collection names are specified in the query
    if 'database' in user_query and 'collection' in user_query:
        if 'and' in user_query:
            db_col = [item.strip() for item in user_query.split("and")]
            if len(db_col) == 2:
                if "collection" in db_col[0] and "database" in db_col[1]:
                    db_name, col_name = db_col[1], db_col[0]
                elif "database" in db_col[0] and "collection" in db_col[1]:
                    db_name, col_name = db_col[0], db_col[1]
                else:
                    return "Unable to determine the database and collection names. Please specify both clearly."
                
                # Store the database and collection names in the session
                cl.user_session.set("db_name", db_name.strip())
                cl.user_session.set("collection_name", col_name.strip())
                full_query = f"{cl.user_session.get('pending_query')} from {db_name} database and {col_name} collection."
                cl.user_session.set("pending_query", None)
                return await cl.make_async(agent.run)(full_query)
        return "Please specify both the database and collection names."

    # If database and collection are not explicitly mentioned, use the last used ones
    if 'database' not in user_query or 'collection' not in user_query:
        if cl.user_session.get("db_name") and cl.user_session.get("collection_name"):
            user_query = f"Use the previously used database ({cl.user_session.get('db_name')}) and collection ({cl.user_session.get('collection_name')}) for this query. {user_query}"
        else:
            cl.user_session.set("pending_query", user_query)
            return "Please specify both the database and collection names."

    try:
        response = await cl.make_async(agent.run)(user_query)
        if isinstance(response, list):
            df = pd.DataFrame(flatten_result(response))
            return df
        return response
    except Exception as e:
        return f"Error handling query: {str(e)}"

mongodb_tool = Tool(
    name="MongoDB Query Tool",
    func=execute_mongodb_query,
    description="Use this tool to execute MongoDB queries. Input should be a dictionary with keys: database, collection, filter, limit, and sort."
)

agent = initialize_agent(
    tools=[mongodb_tool],
    llm=ollama,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
)

@cl.on_chat_start
async def start():
    cl.user_session.set("memory_manager", CustomMemoryManager(ollama))
    cl.user_session.set("db_name", None)
    cl.user_session.set("collection_name", None)
    cl.user_session.set("pending_query", None)
    
    await cl.Message(
        content="Welcome to MongoDB Query Chatbot! Please specify both database and collection names in your queries."
    ).send()

@cl.on_message
async def main(message: cl.Message):
    memory_manager = cl.user_session.get("memory_manager")
    
    response = await handle_user_query_with_tool(message.content, memory_manager)
    
    if isinstance(response, pd.DataFrame):
        table_message = cl.Message(content="DataFrame Result:")
        elements = [
            cl.Pandas(value=response, name="query_result")
        ]
        await table_message.send(elements=elements)
    else:
        await cl.Message(content=str(response)).send()
    
    memory_manager.add_interaction(message.content, response)
    
    # Display summary if just created
    history = memory_manager.get_history()
    latest_entry = history[-1] if history else None
    if latest_entry and latest_entry.get("is_summary", False):
        await cl.Message(content=latest_entry['bot']).send()