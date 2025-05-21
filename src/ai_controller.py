import logging
import os

from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

settings = {
    "model": "gpt-4o-mini",
}

logger = logging.getLogger("webtext2sql")


# This function cannot get a caching decorator because it is async and there is no async cache decorator in cachetools yet
# Possibly, see https://pypi.org/project/asyncache/
async def get_ai_response(prompt: str) -> str:
    """
    Get a response from the AI model based on the provided prompt and settings.

    Args:
        prompt (str): The prompt to send to the AI model.
        settings (dict): The settings for the AI model.

    Returns:
        str: The response from the AI model.
    """
    logger.debug(f"Sending prompt to AI model: {prompt}")

    # Send the prompt to the AI model and get the response
    response = await client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
        **settings,
    )

    return response.choices[0].message.content.strip()
