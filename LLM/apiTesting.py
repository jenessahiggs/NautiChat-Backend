import pandas as pd
import asyncio
from groq import Groq
import json
import os
import pprint
from onc import ONC
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import httpx
from datasets import load_dataset
from langchain.docstore.document import Document
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
ONC_TOKEN = os.getenv("ONC_TOKEN")
CAMBRIDGE_LOCATION_CODE = os.getenv("CAMBRIDGE_LOCATION_CODE")  # Change for a different location
onc = ONC(ONC_TOKEN)


params = {
    "locationCode": "CBY",
    # "locationCode": CAMBRIDGE_LOCATION_CODE,
}
if CAMBRIDGE_LOCATION_CODE:
    locations = onc.getLocationsTree(params)
else:
    locations = onc.getLocations()

for loc in locations:
    print(loc)
