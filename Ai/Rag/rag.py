import os
import re
from pathlib import Path
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from dotenv import load_dotenv

class Rag:

    def __init__(self, database, mongo, patch):
        self.database = database
        self.mongo = mongo
        load_dotenv()
        self.path = Path(__file__).parent.parent.parent / "Assets" / "document"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.patch = patch
        self.name_list = self.database.get_name_kr_list()


    def extract_text_from_docx(self, path):
        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(paragraphs)

    def regex_split(self, text, pattern):
        parts = re.split(pattern, text)
        headers = re.findall(pattern, text)
        result = []
        for i, part in enumerate(parts):
            if i == 0 and not headers:
                result.append(part.strip())
            elif i < len(headers):
                result.append(f"{headers[i]}{part.strip()}")
        return result

    def embedding_patch_info(self, path, info_type):
        text = self.extract_text_from_docx(path)
        chunks_by_rank = self.regex_split(text, r"\n(?=\d{1,2}위\.)")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=50,
            separators=["\n\n", "\n", "."]
        )
        chunks = []
        for chunk in chunks_by_rank:
            chunks.extend(splitter.split_text(chunk))
        print(len(chunks), "chunnk len")
        print(chunks, "chunnk")
        response = self.client.embeddings.create(model="text-embedding-ada-002", input=chunks)
        vectors = [record.embedding for record in response.data]
        # MongoDB 업서트
        self.mongo.upsert_patch_info_vector(path, chunks, vectors, self.name_list, info_type, self.patch.version)

    def build_query(self, champion, metrics=None):
        parts = [champion]
        if metrics: parts.append(metrics)
        return " ".join(parts)

    def vector_search(self, champion, info_type, patch_version):
        query = self.build_query(champion, "버프")
        response = self.client.embeddings.create(model="text-embedding-ada-002", input=query)
        query_vector = response.data[0].embedding
        self.mongo.vector_search_patch_info(query_vector, champion, info_type, patch_version)

    def update_patch_rag(self):
        self.embedding_patch_info(self.path / "25.8_plummet.docx", "plummet")
        self.embedding_patch_info(self.path / "25.8_sky_rocket.docx", "sky_rocket")
        self.embedding_patch_info(self.path / "25.8_tier_list.docx", "tier_list")
