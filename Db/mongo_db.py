from pymongo import MongoClient
from datetime import datetime
import time
from urllib.parse import quote_plus
import cv2

class MongoDB:
    def __init__(self, db_info):
        self.db_info = db_info
        self.client = None
        self.db = None
        self.collection = None
        self.connect_mongodb()

    def connect_mongodb(self):
        try:
            if self.db_info['type'] == "mongo_atlas":
                self.client = MongoClient(self.db_info["uri"])
            else:
                escaped_username = quote_plus(self.db_info['id'])
                escaped_password = quote_plus(self.db_info['password'])
                uri = f"mongodb://{escaped_username}:{escaped_password}@{self.db_info['uri']}:{self.db_info['port']}/{self.db_info['db']}?authSource={self.db_info['auth_db']}"
                self.client = MongoClient(uri)
            self.db = self.client[self.db_info['db']]
            self.client.server_info()

        except Exception as e:
            print(f"MongoDB 연결 에러: {str(e)}")
            raise e

    def save_interview_transcription(self, result, video_path):
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
            existing = self.find_interview_by_video_path(video_path)
            if existing:
                collection.update_one({"_id": existing['_id']}, {"$set": document})
            else:
                collection.insert_one(document)
        except Exception as e:
            print(f"MongoDB 저장 중 에러 발생: {str(e)}")
            return None

    def find_interview_by_video_path(self, video_path):
        query = {"video_path": video_path}
        return self.db['interview'].find_one(query)

    def save_interview_summary(self, video_path, result):
        existing_doc = self.find_interview_by_video_path(video_path)
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


    def save_lck_video_metadata(self, metadata):
        if not metadata or 'video_id' not in metadata:
            return None
        collection = self.db['lck_video']
        if 'downloaded_at' not in metadata:
            metadata['downloaded_at'] = datetime.now()
        existing = collection.find_one({"video_id": metadata['video_id']})
        if existing:
            update_result = collection.update_one(
                {"video_id": metadata['video_id']},
                {"$set": metadata}
            )
            if update_result.modified_count > 0:
                print(f"비디오 메타데이터 업데이트 완료! (Document ID: {existing['_id']})")
                return existing['_id']
            else:
                print(f"비디오 메타데이터가 변경되지 않았습니다. (Document ID: {existing['_id']})")
                return existing['_id']
        else:
            insert_result = collection.insert_one(metadata)
            return insert_result.inserted_id

    def find_lck_video_by_id(self, video_id):
        try:
            return self.db['lck_video'].find_one({"video_id": video_id})
        except Exception as e:
            print(f"비디오 검색 중 오류 발생: {str(e)}")
            return None

    def find_lcK_video_by_video_path(self, video_path):
        query = {"video_path": video_path}
        return self.db['lck_video'].find_one(query)

    def get_all_lck_videos(self, limit=100, sort_by='downloaded_at', sort_order=-1):
        try:
            cursor = self.db['lck_video'].find().sort(sort_by, sort_order).limit(limit)
            return list(cursor)
        except Exception as e:
            print(f"비디오 목록 가져오기 중 오류 발생: {str(e)}")
            return []

    def find_lck_videos_by_date_range(self, start_date, end_date):
        try:
            query = {
                "downloaded_at": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
            cursor = self.db['lck_video'].find(query).sort("downloaded_at", -1)
            return list(cursor)
        except Exception as e:
            print(f"날짜 범위로 비디오 검색 중 오류 발생: {str(e)}")
            return []

    def find_lck_video_by_keyword(self, keyword):
        query = {
            "title": {"$regex": keyword, "$options": "i"}
        }
        cursor = self.db['lck_video'].find(query).sort("downloaded_at", -1)
        return list(cursor)

    def find_lck_video_with_all_keywords_regex(self, keywords_list):
        regex_conditions = [{"title": {"$regex": keyword, "$options": "i"}} for keyword in keywords_list]
        query = {"$and": regex_conditions}
        cursor = self.db['lck_video'].find(query).sort("downloaded_at", -1)
        return list(cursor)

    def find_lck_video_by_keyword_index(self, keyword, date=None):
        query = {
            "$text": {
                "$search":keyword
            }
        }
        if date:
            query["upload_date"] = {"$gte": date}
        cursor = self.db['lck_video'].find(query).sort("downloaded_at", -1)
        return list(cursor)

    def find_lck_video_with_all_keywords_index(self, keywords_list):
        keywords_string = " ".join(["+" + keyword for keyword in keywords_list])
        query = {
            "$text": {
                "$search": keywords_string
            }
        }
        cursor = self.db['lck_video'].find(query).sort("downloaded_at", -1)
        return list(cursor)

    def save_thumbnail_selection(self, _id, thumbnail_data):
        try:
            collection = self.db['lck_video']
            update_data = {
                "$set": {
                    "thumbnail": {
                        "path": thumbnail_data.get("path"),
                        "score": thumbnail_data.get("score"),
                        "criteria_scores": thumbnail_data.get("criteria_scores"),
                        "created_at": datetime.now()
                    }
                }
            }

            update_result = collection.update_one({"_id": _id}, update_data)

            if update_result.modified_count > 0:
                print(f"썸네일 정보가 MongoDB에 저장되었습니다! (Video ID: {_id})")
                return True
            else:
                print(f"썸네일 정보 저장에 실패했습니다. 문서가 변경되지 않았습니다. (Video ID: {_id})")
                return False

        except Exception as e:
            print(f"썸네일 정보 저장 중 오류 발생: {str(e)}")
            return False

    def close(self):
        if self.client:
            self.client.close()