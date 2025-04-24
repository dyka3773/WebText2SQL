import chainlit as cl
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import sqlite3 as sql

import db_controller
import str_manipulation


load_dotenv()

cl.instrument_openai()

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
connection = sql.connect(os.getenv('TARGET_DATABASE_URL'))

settings = {
    "model": "gpt-4o-mini",
}

@cl.on_chat_start
async def present_the_available_dbs_to_user():
    """
    Present the available databases to the user when the chat starts.
    This function is triggered when a new chat session begins.
    """
    # Step 1: Get the list of available databases from the database controller
    # db_list = db_controller.get_available_dbs(user, password) # TODO: Implement this function
    db_list = ["db1", "db2", "db3"]  # Placeholder for the actual database list
    
    action_btns: list[cl.Action] = [
        cl.Action(name="db_selection_btn", payload={"value": db_name}, label=f"Choose {db_name}") for db_name in db_list
    ]
    
    # Step 2: Send a blocking message to the user with the list of available databases
    res = await cl.AskActionMessage(
        content="Please choose a database to work with before sending any messages:", 
        actions=action_btns
    ).send()
    
    # Step 3: Get the selected database name from the action payload
    db_to_work_with = res.get("payload").get("value")
    if db_to_work_with:
        # Step 4: Connect to the selected database and store the connection as a context variable for this user
        # connection = db_controller.connect_to_db(db_to_work_with)  # TODO: Implement this function
        cl.user_session.set("db_connection", db_to_work_with)
        
        # Step 5: Send a message to the user confirming the selection
        await cl.Message(
            content=f"You have selected the database: \n**{db_to_work_with}**\n\nNow you can ask me any question about this database, and I will provide you with the SQL query to get the answer."
        ).send()
    else:
        await cl.Message(
            content="No database selected. Please choose a database to work with."
        ).send()

@cl.on_message
async def handle_message(message: cl.Message):
    """
    Handle incoming messages in each chat.
    This function is triggered whenever a message is sent in the chat.

    Parameters:
        message (cl.Message): The incoming message object.
    """
    # Step 1: Find Metadata from db
    metadata: dict = db_controller.get_db_metadata(connection)
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
    response_str = ai_response.choices[0].message.content.strip()
    
    sql_query = str_manipulation.extract_sql_only(response_str)
    if not sql_query:
        await cl.Message(
            content="The AI model did not return a valid SQL query."
        ).send()
        return
    
    results = db_controller.fetch_data(sql_query, connection)

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
