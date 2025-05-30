import os
from pathlib import Path

import boto3
from datetime import datetime

from PIL import Image
from botocore.exceptions import ClientError
from io import BytesIO
import requests as re

class S3Manager:

    def __init__(self):
        self.s3 = boto3.client('s3')
        self.bucket = "lolstory-s3-bucket"


    def get_all_today_image(self):
        try:
            today = datetime.now().strftime('%y_%m_%d')
            subdirectories = ["Interview", "MatchResult", "PickRate"]
            image_list = {}
            for article_type in subdirectories:
                prefix = f"{article_type}/{today}/"
                response = self.s3.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=prefix,
                )
                if 'Contents' not in response:
                    continue
                for obj in response['Contents']:
                    key = obj['Key']
                    parts = key.split('/')
                    category = parts[0]
                    article_id = parts[2]
                    file_name = parts[-1]
                    url = f"https://{self.bucket}.s3.amazonaws.com/{obj['Key']}"
                    image_list.setdefault(category, {}).setdefault(article_id, []).append({
                        'name': file_name,
                        'url': url
                    })
            #정렬
            for category in image_list:
                for article_id in image_list[category]:
                    image_list[category][article_id].sort(key=lambda x: int(x['name'].split('.')[0]))
            return image_list
        except ClientError as e:
            print(f"S3 List Error: {e}")
            return {}
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return {}

    def get_article_images(self, article_id, article_type, date_str):
        try:
            prefix = f"{article_type}/{date_str}/{article_id}/"
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            if 'Contents' not in response:
                return []

            images = []
            for obj in response['Contents']:
                file_name = obj['Key'].split('/')[-1]
                url = f"https://{self.bucket}.s3.amazonaws.com/{obj['Key']}"
                images.append({
                    'name': file_name,
                    'url': url
                })
            images.sort(key=lambda x: x['name'])
            return images

        except ClientError as e:
            print(f"S3 List Error: {e}")
            return []
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return []

    #오늘날짜 생성 기사 s3로 전송
    def upload_today_folders(self):
        today_str = datetime.now().strftime("%y_%m_%d")
        uploaded_files = []
        errors = []
        subdirectories = ["Interview", "MatchResult", "PickRate"]
        root_dir = Path(__file__).parent.parent / "ImageOutput"
        try:
            for subdir in subdirectories:
                subdir_path = root_dir / subdir
                today_folder = subdir_path / today_str
                if not today_folder.exists():
                    continue

                for dirpath, dirnames, filenames in os.walk(today_folder):
                    for filename in filenames:
                        file_path = os.path.join(dirpath, filename)
                        img = Image.open(file_path).convert("RGB")
                        buffer = BytesIO()
                        img.save(buffer, format="JPEG")
                        buffer.seek(0)
                        rel_path = os.path.relpath(file_path, root_dir)
                        rel_path_jpg = os.path.splitext(rel_path)[0] + '.jpg'
                        s3_key = f"{rel_path_jpg}".replace("\\", "/")

                        self.s3.upload_fileobj(
                            buffer,
                            self.bucket,
                            s3_key,
                            ExtraArgs = {
                                'ContentType': 'image/jpeg'
                            }
                        )

                        uploaded_files.append({
                            'local_path': file_path,
                            's3_key': s3_key,
                            's3_url': f"https://{self.bucket}.s3.amazonaws.com/{s3_key}"
                        })

            return {
                'success': len(errors) == 0,
                'uploaded_count': len(uploaded_files),
                'uploaded_files': uploaded_files,
                'errors': errors
            }
        except Exception as e:
            return {
                'success': False,
                'uploaded_count': len(uploaded_files),
                'uploaded_files': uploaded_files,
                'errors': errors + [f"Unexpected error: {str(e)}"]
            }