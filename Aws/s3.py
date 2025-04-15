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
        self.upload_path = "/"


    def upload_image(self, image, upload_path, article_id, image_name):
        try:
            buffer = BytesIO()
            image.save(buffer, format('JPEG'))
            buffer.seek(0)
            today = datetime.now().strftime('%Y/%m/%d')
            key = f"{upload_path}/{today}/{article_id}/{image_name}"
            self.s3.upload_fileobj(
                buffer,
                self.bucket,
                key,
                ExtraArgs={
                    'ContentType': 'image/jpeg'
                }
            )
            return key
        except ClientError as e:
            print(f"S3 Upload Error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return None

    def upload_image_url(self, img_source, upload_path, img_name):
        try:
            image_response = re.get(img_source)
            if image_response.status_code == 200:
                s3_key = f"{upload_path}/{img_name}"
                self.s3.upload_fileobj(
                    BytesIO(image_response.content),
                    self.bucket,
                    s3_key,
                    ExtraArgs={'ContentType': 'image/jpeg'}
                )
                return s3_key
            else:
                print(f"URL 이미지 다운로드 실패. Status code: {image_response.status_code}")
                return None
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            return None

    def get_all_today_image(self):
        try:
            today = datetime.now().strftime('%y_%m_%d')
            prefix = ""
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
            )
            if 'Contents' not in response:
                return []
            image_list = {}
            for obj in response['Contents']:
                key_parts = obj['Key'].split("/")
                if len(key_parts) < 4:
                    continue
                category, folder_date, article_id, file_name = key_parts
                if folder_date != today:
                    continue
                url = f"https://{self.bucket}.s3.amazonaws.com/{obj['Key']}"
                image_list.setdefault(category, {}).setdefault(article_id, []).append({
                    'name': file_name,
                    'url': url
                })
            return image_list
        except ClientError as e:
            print(f"S3 List Error: {e}")
            return {}
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return {}

    def get_image_url(self, key, expires_in = 3600):
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': key
                },
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            print(f"URL Generation Error: {e}")
            return None

    def get_article_images(self, article_seq, date_str):
        try:
            formatted_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y/%m/%d')
            prefix = f"{self.upload_path}/{formatted_date}/{article_seq}/"
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

    def upload_today_folders(self, s3_prefix=""):
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
                        s3_key = f"{s3_prefix}/{rel_path_jpg}".replace("\\", "/")

                        self.s3.upload_fileobj(
                            buffer,
                            self.bucket,
                            s3_key,
                            ExtraArgs={'ContentType': 'image/jpeg'}
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