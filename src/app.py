import chainlit as cl
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import psycopg as sql


import custom_logging
logger = custom_logging.setup_logger("webtext2sql")
custom_logging.setup_logger("chainlit")

import db_controller
import str_manipulation


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
    logger.debug(f"A user is trying to log in")
    # TODO: Use the credentials of the db server they want to connect to
    if (username, password) == ("admin", "admin"):
        logger.debug(f"User {username} authenticated successfully")
        
        try:
            connection = sql.connect(os.getenv('TARGET_DATABASE_URL'))
        except sql.Error as e:
            logger.error(f"Error connecting to the database: {e}")
            return None
        
        return cl.User(
            identifier="admin", metadata={"conn_info": connection.info.get_parameters(), "password": connection.info.password},
        )
    else:
        return None

@cl.on_chat_resume
async def on_chat_resume(thread: dict):
    """
    Handle the event when a chat is resumed.
    This function is triggered when a user resumes a chat session.
    
    Parameters:
        thread: The thread object representing the chat session.
    """
    logger.debug(f"Chat resumed: {thread['id']} by User: {thread['userId']}")

@cl.on_chat_start
async def on_chat_start():
    """
    Present the available databases to the user when the chat starts.
    This function is triggered when a new chat session begins.
    
    Parameters:
        thread: The thread object representing the chat session.
    """
    logger.debug(f"Chat started by User: {cl.user_session.get('user').identifier}")
    # Step 1: Get the list of available databases from the database controller
    # db_list = db_controller.get_available_dbs(user, password) # TODO: Implement this function
    db_list = ["northwind", "northwind", "northwind"]  # Placeholder for the actual database list

    action_btns: list[cl.Action] = [
        cl.Action(name=f"{db_name} Queries", payload={"value": db_name}, label=f"Choose {db_name}") for db_name in db_list
    ]

    # Step 2: Send a blocking message to the user with the list of available databases
    res = await cl.AskActionMessage(
        content="Please choose a database schema to work with before sending any messages:", 
        actions=action_btns
    ).send()

    # Step 3: Get the selected database name from the action payload
    schema_to_work_with = res.get("payload").get("value")
    if schema_to_work_with:
        # Step 4: Set the selected schema as a context variable for this user
        cl.user_session.set("db_schema", schema_to_work_with)

        # Step 5: Send a message to the user confirming the selection
        await cl.Message(
            content=f"You have selected the schema: \n**{schema_to_work_with}**\n\nNow you can ask me any question about this database, and I will provide you with the SQL query to get the answer."
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
    logger.debug(f"Received message: {message.content}")
    
    # Step 1: Find Metadata from db according to the user
    conn_info, password = cl.user_session.get("user").metadata["conn_info"], cl.user_session.get("user").metadata["password"]
    conn_info["password"] = password
    
    schema = cl.user_session.get("db_schema")
    
    if not conn_info or not password:
        logger.error("No database connection found in user metadata.")
        await cl.Message(
            content="No database connection found. Please log in again."
        ).send()
        return
    else:
        logger.info(f"Using connection info: {conn_info}") # TODO: Remove this later, it's a security risk
        connection = sql.connect(**conn_info)
        logger.debug(f"Connected to the database with connection info: {conn_info}")
    
    logger.debug(f"Fetching metadata from the database")
    metadata: dict = db_controller.get_db_metadata(connection, schema, conn_info["user"])
    meta_str = "\n".join([f"{table}: {', '.join(columns)}" for table, columns in metadata.items()])

    template = f"""This is my db structure: 
    {meta_str} 
    
    Please answer only with the SQL query (without any text formatting) that answers the following question:
    {message.content}
    
    Keep in mind that the database is a PostgreSQL database and that the schema is {schema} and it should be used in the SQL query.
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
    logger.debug(f"AI response: {response_str}")
    
    sql_query = str_manipulation.extract_sql_only(response_str)
    logger.debug(f"Extracted SQL query: {sql_query}")
    if not sql_query:
        logger.error("The AI model did not return a valid SQL query.")
        await cl.Message(
            content="The AI model did not return a valid SQL query."
        ).send()
        return
    
    results = db_controller.fetch_data(sql_query, connection)

    # Step 5: Format the data into a user-friendly format before and sending it back to the user
    if not results:
        logger.warning("No results found for the SQL query.")
        results = "No results found."
    else:
        results = "\n".join([str(row) for row in results])
        
    answer = f"Here is the SQL query the AI model generated:\n```sql\n{sql_query}\n```\n\nAnd here are the results:\n```\n{results}\n```"

    # Step 6: Send the response back to the user
    await cl.Message(
        content=answer
    ).send()
