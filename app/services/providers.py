"""Lazy clients are reused by warm Lambda execution environments."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def openai_client():
    from openai import OpenAI

    return OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=12.0, max_retries=0)


@lru_cache(maxsize=1)
def pinecone_index():
    from pinecone import Pinecone

    return Pinecone(api_key=os.environ["PINECONE_API_KEY"]).Index(os.environ["PINECONE_INDEX_NAME"])
