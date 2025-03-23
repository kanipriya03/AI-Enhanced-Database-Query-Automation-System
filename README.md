# AI-Enhanced-Database-Query-Automation-System

## Overview
This project is a chatbot that interacts with a MongoDB database using LangChain and Ollama's LLM. The chatbot can execute MongoDB queries, maintain conversation history, and summarize interactions for efficient memory management.

## Features
- Query MongoDB databases and collections.
- Maintain a conversation history with automatic summarization.
- Execute queries using LangChain's agent-based system.
- Utilize an LLM (Hermes 3) for intelligent query processing.
- Provide structured data output as Pandas DataFrames.
- Store and retrieve previous database and collection selections.

## Technologies Used
- **MongoDB** for database storage
- **LangChain** for query execution and memory management
- **ChatOllama** as the LLM for processing queries
- **Chainlit** for chatbot interaction
- **Pandas** for structured data handling

## Installation

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd <repo-folder>
   ```

2. Install dependencies:
   ```bash
   pip install pymongo langchain_community langchain_ollama chainlit pandas
   ```

3. Set up MongoDB connection:
   Update the `MONGODB_URI` with your MongoDB Atlas connection string:
   ```python
   MONGODB_URI = "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority"
   ```

## Usage

### Running the Chatbot
Start the chatbot using Chainlit:
```bash
chainlit run <script_name>.py
```

### Query Format
Queries should be structured as dictionaries containing:
- `database`: Name of the database
- `collection`: Name of the collection
- `filter`: MongoDB filter query (optional)
- `sort`: Sorting criteria (optional)
- `projection`: Fields to return (optional)
- `aggregation`: Aggregation pipeline (optional)

Example Query:
```python
{
    "database": "myDB",
    "collection": "users",
    "filter": {"age": {"$gt": 25}},
    "sort": {"name": 1},
    "projection": {"_id": 0, "name": 1, "age": 1}
}
```

### Conversation History & Summarization
- Stores the last 5 interactions.
- Summarizes and clears older messages to maintain memory efficiency.
- Summaries are displayed periodically.

## Contributions
Feel free to contribute by submitting issues or pull requests.



