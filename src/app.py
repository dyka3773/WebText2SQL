import chainlit as cl
from chainlit.types import ThreadDict
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import psycopg as sql


import custom_logging
logger = custom_logging.setup_logger("webtext2sql")
custom_logging.setup_logger("chainlit")

import db_controller
import str_manipulation
import auth
import chainlit_controller


load_dotenv()

cl.instrument_openai()

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

settings = {
    "model": "gpt-4o-mini",
}


@cl.password_auth_callback
def auth_callback(username: str, password: str) -> cl.User | None:
    """
    Authenticate the user based on the provided username and password.
    This function is called when a user tries to log in to the application.
    
    Parameters:
        username (str): The username provided by the user.
        password (str): The password provided by the user.
        
    Returns:
        cl.User: An instance of the User class if authentication is successful, None otherwise.
    """
    return auth.authenticate_user(username, password, os.getenv('TARGET_DATABASE_URL'))


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """
    Handle the event when a chat is resumed.
    This function is triggered when a user resumes a chat session.
    
    Parameters:
        thread: The thread object representing the chat session.
    """
    logger.debug(f"Chat resumed: {thread['id']} by User: {thread['userId']}")

@cl.on_chat_start
async def force_user_to_choose_db_schema_for_this_chat():
    """
    Present the available database schemas to the user when the chat starts.
    This function is triggered when a new chat session begins.
    
    Parameters:
        thread: The thread object representing the chat session.
    """
    logger.debug(f"Chat started by User: {cl.user_session.get('user').identifier}")
    # Get the list of available database schemas from the database controller        
    db_list = chainlit_controller.get_available_schemas_for_curr_user()
    
    if not db_list:
        logger.error(f"No database schemas found for the user: {cl.user_session.get('user').identifier}")
        await cl.Message(
            content="No database schemas found for you. Please log in again."
        ).send()
        return

    action_btns: list[cl.Action] = [
        cl.Action(name=f"{db_name} Queries", payload={"value": db_name}, label=f"{db_name}") for db_name in db_list
    ]
    
    # Make the user select a schema to work with before sending any messages
    await chainlit_controller.handle_schema_selection(action_btns)


@cl.on_message
async def handle_message(message: cl.Message):
    """
    Handle incoming messages in each chat.
    This function is triggered whenever a message is sent in the chat.

    Parameters:
        message (cl.Message): The incoming message object.
    """
    logger.debug(f"Received message: {message.content}")
    
    # Step 1: Find Metadata from db according to the user
    conn_info = chainlit_controller.get_user_connection_info()
    
    if not conn_info: # I don't know if this can happen, but just in case
        logger.error("Connection info not found for the user but the user is logged in.")
        await cl.Message(
            content="Database connection lost. Please try again later."
        ).send()
        return
    else:
        connection: sql.Connection = sql.connect(**conn_info)
    
    # I'm kinda worried this might not be set correctly and that it takes the schema from the user session and not the thread session
    schema = cl.user_session.get("db_schema") 
    
    logger.debug(f"Fetching metadata from the database")
    metadata: list[str] = db_controller.get_db_metadata(connection, schema, conn_info["user"])
    meta_str = "\n".join(metadata)

    template = f"""This is my db structure: 
    {meta_str} 
    
    Please answer only with the SQL query (without any text formatting) that answers the following question:
    {message.content}
    
    Keep in mind that the database is a PostgreSQL database and that the schema is {schema} and it should be used in the SQL query.
    """
    # Step 2: Send user's query to AI & get the response from AI in the form of a SQL query
    ai_response = await client.chat.completions.create(
        messages=[
            {"role": "user", "content": template}
        ],
        **settings,
    )

    # Step 3: Execute the SQL query against the database
    response_str = ai_response.choices[0].message.content.strip()
    logger.debug(f"AI's response: {response_str}")
    
    # TODO: Wrap below until Step 4 in a function to make it cleaner
    sql_query = str_manipulation.extract_sql_only(response_str)
    logger.debug(f"Extracted SQL query: {sql_query}")
    if not sql_query:
        logger.error("The AI model did not return a valid SQL query.")
        await cl.Message(
            content="The AI model did not return a valid SQL query."
        ).send()
        return
    
    results = db_controller.fetch_data(sql_query, connection)

    # Step 4: Format the data into a user-friendly format before and sending it back to the user
    # TODO: Wrap below in a function to make it cleaner
    if not results:
        logger.warning("No results found for the SQL query.")
        results = "No results found."
    else:
        # TODO: Format the results into a more user-friendly format. See #1
        results = "\n".join([str(row) for row in results])
        
    answer = f"Here is the SQL query the AI model generated:\n```sql\n{sql_query}\n```\n\nAnd here are the results:\n```\n{results}\n```"

    # Step 5: Send the response back to the user
    await cl.Message(
        content=answer
    ).send()
