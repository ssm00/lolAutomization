import os
import sys
import pymysql
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))))

class Database:
    def __init__(self, db_info, logger):
        try:
            self.type = db_info["type"]
            self.db = pymysql.connect(
                host=db_info['host'],
                user=db_info['id'],
                password=db_info['password'],
                db=db_info['db'],
                charset='utf8mb4',
            )
            self.cursor = self.db.cursor(pymysql.cursors.DictCursor)
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise

    def execute(self, query, args=None):
        return self.cursor.execute(query, args)

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

    def create_job(self, job_name):
        start_time = datetime.now()
        query = """INSERT INTO batch_jobs (job_name, status, start_time) VALUES (%s, %s, %s)"""
        value = (job_name, 'RUNNING', start_time)
        result = self.execute(query, value)
        self.commit()
        return self.cursor.lastrowid

    def update_job_status(self, job_id, status, duration, formatted_duration, end_time=None, error_message=None):
        end_time = end_time or datetime.now()
        query = """UPDATE batch_jobs 
            SET status = %s,
                end_time = %s,
                error_message = %s,
                duration = %s,
                formatted_duration = %s
            WHERE id = %s
        """
        self.execute(query, (
            status,
            end_time,
            error_message,
            duration,
            formatted_duration,
            job_id
        ))
        self.commit()

    def get_all_running_job(self):
        query = "select id, start_time from batch_jobs where status = 'RUNNING'"
        return self.fetch_all(query)

    def stop_job(self, id, end_time, duration, formatted_duration):
        query = """UPDATE batch_jobs SET status = 'STOPPED', end_time = %s, duration = %s, formatted_duration = %s WHERE id = %s """
        self.execute(query, (end_time, duration, formatted_duration, id))
        self.commit()
