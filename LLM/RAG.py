from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from qdrant_client.http.models import VectorParams, Distance
import pandas as pd


class JinaEmbeddings(Embeddings):
    def __init__(self, task="retrieval.document"):
        print("Creating Jina Embeddings instance...")
        self.model = SentenceTransformer("jinaai/jina-embeddings-v3", trust_remote_code=True)
        print("Jina Embeddings instance created.")
        self.task = task

    def embed_documents(self, texts):
        return self.model.encode(texts, task=self.task, prompt_name=self.task)

    def embed_query(self, text):
        return self.model.encode([text], task="retrieval.query", prompt_name="retrieval.query")[0]


class RAG:
    def __init__(self, qdrant_url: str, collection_name: str, qdrant_api_key: str):
        self.qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        self.collection_name = collection_name
        print("Creating Jina Embeddings instance...")
        self.embedding = JinaEmbeddings()
        print("Creating Qdrant instance...")
        self.qdrant = Qdrant(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embeddings=self.embedding,
            content_payload_key="text",
        )
        # Qdrant Retriever
        print("Creating Qdrant retriever...")
        self.retriever = qdrant.as_retriever(search_kwargs={"k": 3})
        # Reranker (from RerankerNoGroq notebook)
        print("Creating CrossEncoder model...")
        self.model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        self.compressor = CrossEncoderReranker(model=self.model, top_n=3)
        print("Creating ContextualCompressionRetriever...")
        self.compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor, base_retriever=self.retriever
        )

    def get_documents(self, question: str):
        compression_documents = self.compression_retriever.invoke(question)
        compression_contents = [doc.page_content for doc in compression_documents]
        df = pd.DataFrame({"contents": compression_contents})
        return df

    def create_vector_store(self, data: pd.DataFrame):
        """Create a vector store from a DataFrame."""
        vector_store = Qdrant.from_documents(
            documents=data.to_dict(orient="records"),
            embedding=self.embeddings,
            collection_name=self.collection_name,
            client=self.qdrant_client,
        )
        return vector_store

    def get_retriever(self, top_k: int = 5):
        """Get a retriever with compression."""
        cross_encoder = HuggingFaceCrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        reranker = CrossEncoderReranker(cross_encoder=cross_encoder)
        retriever = ContextualCompressionRetriever(
            base_retriever=Qdrant(self.qdrant_client, self.collection_name), document_compressor=reranker, k=top_k
        )
        return retriever
