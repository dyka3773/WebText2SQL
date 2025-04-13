import chainlit as cl
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import sqlite3 as sql

import DbController


load_dotenv()

cl.instrument_openai()

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
connection = sql.connect(os.getenv('TARGET_DATABASE_URL'))

settings = {
    "model": "gpt-4o-mini",
}


@cl.on_message
async def handle_message(message: cl.Message):
    """
    Handle incoming messages in each chat.
    This function is triggered whenever a message is sent in the chat.

    Parameters:
        message (cl.Message): The incoming message object.
    """
    # Step 1: Find Metadata from db
    metadata: dict = DbController.get_db_metadata(connection)
    meta_str = "\n".join([f"{table}: {', '.join(columns)}" for table, columns in metadata.items()])

    template = f"""This is my db structure: 
    {meta_str} 
    
    Please answer only with the SQL query (without any text formatting) that answers the following question:
    {message.content}
    """
    # Step 2: Send user's query and metadata to AI

    # Step 3: Get the response from AI in the form of a SQL query
    ai_response = await client.chat.completions.create(
        messages=[
            {"role": "user", "content": template}
        ],
        **settings,
    )

    # Step 4: Execute the SQL query against the database
    sql_query = ai_response.choices[0].message.content.strip()
    results = DbController.fetch_data(sql_query, connection)

    # Step 5: Format the data into a user-friendly format before and sending it back to the user
    if not results:
        results = "No results found."
    else:
        results = "\n".join([str(row) for row in results])
        
    answer = f"Here is the SQL query the AI model generated:\n```sql\n{sql_query}\n```\n\nAnd here are the results:\n```\n{results}\n```"

    # Step 6: Send the response back to the user
    await cl.Message(
        content=answer
    ).send()
