from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import psycopg2

class Postgres:

    def __init__(self, db_info, logger):
        self.conn = psycopg2.connect(
            dbname=db_info['db'],
            user=db_info['id'],
            password=db_info['password'],
            host=db_info['host'],
            port=db_info['port']
        )
        self.embeddings = HuggingFaceEmbeddings(
            model_name="jhgan/ko-sroberta-multitask"
        )
        self.logger = logger
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        # 데이터베이스 초기 설정
        #self._setup_database()

    def _setup_database(self):
        """데이터베이스 초기 설정: pgvector 확장 및 테이블 생성"""
        with self.conn.cursor() as cur:
            # pgvector 확장 설치
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # 패치노트 청크를 저장할 테이블 생성
            cur.execute("""
                CREATE TABLE IF NOT EXISTS patch_note_chunks (
                    id SERIAL PRIMARY KEY,
                    patch_version TEXT,
                    content TEXT,
                    embedding vector(768),  # 임베딩 차원 수에 맞게 설정
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 벡터 검색을 위한 인덱스 생성
            cur.execute("""
                CREATE INDEX IF NOT EXISTS patch_note_chunks_embedding_idx 
                ON patch_note_chunks 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)

            self.conn.commit()

    def process_patch_note(self, patch_text, patch_version):
        """패치노트 텍스트를 처리하여 데이터베이스에 저장"""
        # 텍스트를 청크로 분할
        chunks = self.text_splitter.split_text(patch_text)

        # 청크별로 임베딩 생성 및 저장 데이터 준비
        data = []
        for chunk in chunks:
            # 청크의 임베딩 벡터 생성
            embedding = self.embeddings.embed_query(chunk)

            data.append((
                patch_version,
                chunk,
                embedding
            ))

        # 데이터베이스에 일괄 저장
        with self.conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO patch_note_chunks (patch_version, content, embedding)
                VALUES %s
            """, data)

        self.conn.commit()

    def search_similar_content(self, query, limit=5):
        """쿼리와 유사한 패치노트 내용 검색"""
        # 쿼리 텍스트의 임베딩 벡터 생성
        query_embedding = self.embeddings.embed_query(query)

        # 벡터 유사도 검색 수행
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT content, patch_version, 
                       1 - (embedding <=> %s) as similarity
                FROM patch_note_chunks
                ORDER BY embedding <=> %s
                LIMIT %s
            """, (query_embedding, query_embedding, limit))

            results = cur.fetchall()

        # 검색 결과 정리
        return [
            {
                'content': content,
                'patch_version': version,
                'similarity': float(similarity)
            }
            for content, version, similarity in results
        ]

