from pymongo import MongoClient
from datetime import datetime
import time
from urllib.parse import quote_plus


class MongoDB:
    def __init__(self, db_info):
        self.db_info = db_info
        self.client = None
        self.db = None
        self.collection = None
        self.connect_mongodb()

    def connect_mongodb(self):
        try:
            escaped_username = quote_plus(self.db_info['id'])
            escaped_password = quote_plus(self.db_info['password'])

            uri = f"mongodb://{escaped_username}:{escaped_password}@{self.db_info['uri']}:{self.db_info['port']}/{self.db_info['db']}?authSource={self.db_info['auth_db']}"
            self.client = MongoClient(uri)
            self.db = self.client[self.db_info['db']]
            self.client.server_info()

        except Exception as e:
            print(f"MongoDB 연결 에러: {str(e)}")
            raise e

    def save_transcription(self, result, video_path):
        if result is None:
            print("저장할 결과가 없습니다.")
            return None

        try:
            collection = self.db['interview']

            document = {
                "video_path": video_path,
                "created_at": datetime.now(),
                "full_text": result["text"],
                "metadata": {
                    "model_language": result.get("language", ""),
                    "duration": result.get("duration", 0),
                },
                "segments": [
                    {
                        "start_time": time.strftime('%H:%M:%S', time.gmtime(segment["start"])),
                        "end_time": time.strftime('%H:%M:%S', time.gmtime(segment["end"])),
                        "text": segment["text"].strip(),
                        "start": segment["start"],
                        "end": segment["end"],
                        "confidence": segment.get("confidence", 0)
                    }
                    for segment in result["segments"]
                ]
            }

            insert_result = collection.insert_one(document)
            print(f"MongoDB에 저장 완료! (Document ID: {insert_result.inserted_id})")
            return insert_result.inserted_id

        except Exception as e:
            print(f"MongoDB 저장 중 에러 발생: {str(e)}")
            return None

    def find_by_video_path(self, video_path):
        query = {"video_path": video_path}
        return self.db['interview'].find_one(query)

    def save_interview_summary(self, result, video_path):
        existing_doc = self.find_by_video_path(video_path)
        collection = self.db['interview']
        update_data = {
            "$set": {
                "summary": {
                    "main_title": result['main_title'],
                    "summaries": result["summaries"],
                    "created_at": datetime.now()
                }
            }
        }
        update_result = collection.update_one({"_id": existing_doc["_id"]}, update_data)
        if update_result.modified_count > 0:
            print(f"인터뷰 요약이 MongoDB에 저장되었습니다! (Document ID: {existing_doc['_id']})")
            return existing_doc["_id"]
        else:
            print("인터뷰 요약 저장에 실패했습니다. 문서가 변경되지 않았습니다.")
            return None

    def close(self):
        if self.client:
            self.client.close()