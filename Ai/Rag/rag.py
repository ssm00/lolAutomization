import os
from pathlib import Path
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from dotenv import load_dotenv

class Rag:

    def __init__(self, mongo, patch):
        self.mongo = mongo
        load_dotenv()
        self.path = Path(__file__).parent.parent.parent / "Assets" / "document"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.patch = patch

    def extract_text_from_docx(self, path):
        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(paragraphs)

    def embedding_patch_info(self, path, info_type):
        text = self.extract_text_from_docx(path)
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = splitter.split_text(text)
        response = self.client.embeddings.create(model="text-embedding-ada-002", input=text)
        vectors = [record.embedding for record in response.data]
        # MongoDB 업서트
        self.mongo.upsert_patch_info_vector(path, chunks, vectors, info_type, self.patch.version)

    def build_query(self, champion, metrics=None):
        parts = [champion]
        if metrics: parts.append(metrics)
        return " ".join(parts)

    def vector_search(self, champion, info_type, patch_version):
        query = self.build_query(champion, "버프")
        response = self.client.embeddings.create(model="text-embedding-ada-002", input=query)
        query_vector = response.data[0].embedding
        self.mongo.vector_search_patch_info(query_vector, info_type, patch_version)

    def update_patch_rag(self):
        self.embedding_patch_info(self.path / "25.8_plummet.docx", "plummet")
        self.embedding_patch_info(self.path / "25.8_sky_rocket.docx", "sky_rocket")
        self.embedding_patch_info(self.path / "25.8_tier_list.docx", "tier_list")
