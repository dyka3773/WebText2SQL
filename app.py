import chainlit as cl

from DbController import fetch_data, connection


@cl.on_message
async def handle_message(message: cl.Message):
    """
    Handle incoming messages in each chat.
    This function is triggered whenever a message is sent in the chat.

    Parameters:
        message (cl.Message): The incoming message object.
    """
    # Step 1: Find Metadata from db
    
    # Step 2: Send user's query and metadata to AI
    
    # Step 3: Get the response from AI in the form of a SQL query
    
    # Step 4: Execute the SQL query against the database
    results = fetch_data(message.content, connection)
    
    # Step 5: Format the data into a user-friendly format before and sending it back to the user
    
    
    await cl.Message(
        content=results
    ).send()
