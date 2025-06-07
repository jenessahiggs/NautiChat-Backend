import os
import fitz  # PyMuPDF
import nltk
from nltk.tokenize import sent_tokenize
from collections import Counter
from RAG import JinaEmbeddings
from RAG import QdrantClientWrapper
from uuid import uuid4
from qdrant_client.models import PointStruct

'''
Series of functions to preprocess PDF files, extract structured text chunks,
and embeds them using a Jina Model. Includes handler to upload embedded data to a vector database.

Usage:
1. Call `prepare_embedding_input(file_path)` with the path to the PDF file. Optionally, you can pass a `JinaEmbeddings` instance to use a specific embedding model. If no embedding model is provided, a default instance will be created.
2. This function will return a list of dictionaries, each containing:
   - `id`: Unique identifier for the chunk.
    - `embedding`: The embedding vector for the chunk.
    - `text`: The text content of the chunk.
    - `metadata`: Additional metadata source file, section heading, page number, and chunk index.
3. Call `upload_to_vector_db(resultsList, qdrant)` to upload the list of results to a Qdrant vector database.

To speed up use assumes that the embedding model and qdrant client are being used from the RAG module.
'''

def extract_structured_chunks(file_path):
    doc = fitz.open(file_path)
    structured = []

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:  # text
                for line in block["lines"]:
                    #print(line)
                    line_text = " ".join(span["text"] for span in line["spans"]).strip()
                    if not line_text:
                        continue
                    avg_font_size = sum(span["size"] for span in line["spans"]) / len(line["spans"])
                    min_x = min(span["origin"][0] for span in line["spans"])
                    min_y = min(span["origin"][1] for span in line["spans"])
                    origin = (min_x, min_y)
                    structured.append({
                        "text": line_text,
                        "page": page_num,
                        "font_size": avg_font_size,
                        "origin" : origin
                    })
    structured.sort(key=lambda x: (x["origin"][1], x["origin"][0]))
    return structured

def detect_main_body_font_size(structured_chunks):
    font_sizes = [round(chunk["font_size"], 1) for chunk in structured_chunks]
    font_size_counts = Counter(font_sizes)

    sorted_font_sizes = font_size_counts.most_common()

    #print("Detected font sizes (sorted by frequency):")
    #for size, count in sorted_font_sizes:
        #print(f"  Font size: {size} → {count} occurrences")

    # Assume the most common font size is the body text
    main_body_font_size = sorted_font_sizes[0][0] if sorted_font_sizes else None
    return main_body_font_size


def group_sections(chunks):
    sections = []
    body_size = detect_main_body_font_size(chunks)
    current_section = {"heading": None, "paragraphs": [], "page": []}

    for chunk in chunks:
        if chunk["font_size"] > body_size:
            if current_section["heading"] != None:
                sections.append(current_section)
                current_section = {"heading": None, "paragraphs": [], "page": [chunk["page"]]}
            current_section["heading"] = chunk["text"]
        else:
            current_section["paragraphs"].append(chunk["text"])
        if chunk["page"] not in current_section["page"]:
            current_section["page"].append(chunk["page"])

    if current_section["paragraphs"] or current_section["heading"]:
        sections.append(current_section)

    return sections



#Default to small max tokens for better search and matching and faster
def chunk_text_with_heading(text, heading="", max_tokens=300, overlap=50):
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt_tab')

    sentences = sent_tokenize(text)
    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        tokens = len(sentence.split())  # word-based token approximation

        # If adding this sentence would exceed the token limit
        if current_len + tokens > max_tokens:
            chunk_body = " ".join(current)
            chunk_text = f"{heading}\n{chunk_body}".strip()
            chunks.append(chunk_text)

            # Create overlap
            current = current[-overlap:] if overlap > 0 else []
            current_len = sum(len(s.split()) for s in current)

        current.append(sentence)
        current_len += tokens

    # Final chunk
    if current:
        chunk_body = " ".join(current)
        chunk_text = f"{heading}\n{chunk_body}".strip()
        chunks.append(chunk_text)

    return chunks

def prepare_embedding_input(file_path: str, embedding_model: JinaEmbeddings = None):
    structured_chunks = extract_structured_chunks(file_path)
    sections = group_sections(structured_chunks)
    results = []

    for section in sections:
        full_text = " ".join(section["paragraphs"])
        chunks = chunk_text_with_heading(full_text, section["heading"])

        if embedding_model is None:
            embedding_model = JinaEmbeddings()
        embeddings = embedding_model.embed_documents(chunks)

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            results.append({
                "id": f"{os.path.basename(file_path)}_chunk_{i}",
                "embedding": embedding.tolist(),
                "text": chunk,
                "metadata": {
                    "source": os.path.basename(file_path),
                    "section_heading": section["heading"],
                    "page": section["page"],
                    "chunk_index": i
                }
            })

    return results


def upload_to_vector_db(resultsList: list, qdrant: QdrantClientWrapper):
    points = []
    for item in resultsList:
        points.append(
            PointStruct(
                id=uuid4().hex,
                vector=item["embedding"],
                payload={
                    "text": item["text"],
                    **item["metadata"]
                }
            )
        )

    qdrant.qdrant_client.upload_points(
        collection_name=qdrant.collection_name,
        points=points
    )