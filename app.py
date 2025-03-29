import chainlit as cl

from DbController import fetch_data, connection


@cl.on_message
async def handle_message(message: cl.Message):
    """
    Handle incoming messages in the Chainlit application.

    Parameters:
        message (cl.Message): The incoming message object.
    """
    results = fetch_data(message.content, connection)
    await cl.Message(
        content=results
    ).send()
