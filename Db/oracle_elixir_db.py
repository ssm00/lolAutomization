import os
import sys
import pymysql
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))))


class Database:
    def __init__(self, db_info, logger):
        self.db_info = db_info
        self.logger = logger
        self.db = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.db = pymysql.connect(
                host=self.db_info['host'],
                user=self.db_info['id'],
                password=self.db_info['password'],
                db=self.db_info['db'],
                charset='utf8mb4',
            )
            self.cursor = self.db.cursor(pymysql.cursors.DictCursor)
            self.logger.info("데이터베이스 연결 성공")
        except Exception as e:
            self.logger.error(f"데이터베이스 연결 실패: {e}")
            raise

    def save_article_info(self, basic_article_info):
        query = f"""INSERT IGNORE INTO article (article_id, original_title, original_content, href, article_type, published_at, collected_at) VALUES (%s,%s,%s,%s,%s,%s,%s)"""
        values = (basic_article_info.article_id, basic_article_info.original_title, basic_article_info.original_content,
                  basic_article_info.href, basic_article_info.article_type, basic_article_info.published_at,
                  datetime.now().strftime("%y-%m-%d %H:%M:S"))
        self.cursor.execute(query, values)
        self.commit()

    def fetch_all(self, query, args=None):
        self.cursor.execute(query, args)
        return self.cursor.fetchall()

    def fetch_one(self, query, args=None):
        self.cursor.execute(query, args)
        return self.cursor.fetchone()

    def commit(self):
        self.db.commit()

    def close(self):
        self.db.close()
