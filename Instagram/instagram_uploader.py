import requests
import time
from Aws.s3 import S3Manager


class InstagramUploader:

    """
        인스타 게시 플로우
        1. 캐러셀 아이템 생성
        2. 캐러셀 컨테이너 생성
        3. 게시
    """ 
    def __init__(self, account_info, logger):
        self.access_token = account_info.get("instagram").get("access_token")
        self.account_id = account_info.get("instagram").get("account_id")
        self.api_version = account_info.get("instagram").get("api_version")
        self.graph_url = f'https://graph.facebook.com/{self.api_version}'
        self.base_content = account_info.get("instagram").get("base_content")
        self.logger = logger
        self.s3 = S3Manager()

    def create_carousel_item(self, image_url):
        params = {
            'image_url': image_url,
            'is_carousel_item': 'true',
            'access_token': self.access_token
        }

        url = f'{self.graph_url}/{self.account_id}/media'
        response = requests.post(url, params=params)

        if response.status_code != 200:
            raise Exception(f"Error creating carousel item: {response.text}")

        return response.json().get('id')

    def create_carousel_container(self, caption, carousel_items):
        params = {
            'media_type': 'CAROUSEL',
            'caption': caption,
            'children': ','.join(carousel_items),
            'access_token': self.access_token
        }
        url = f'{self.graph_url}/{self.account_id}/media'
        response = requests.post(url, params=params)
        if response.status_code != 200:
            raise Exception(f"Error creating carousel container: {response.text}")
        return response.json().get('id')

    def publish_carousel(self, container_id):
        params = {
            'creation_id': container_id,
            'access_token': self.access_token
        }

        url = f'{self.graph_url}/{self.account_id}/media_publish'
        response = requests.post(url, params=params)

        if response.status_code != 200:
            raise Exception(f"Error publishing carousel: {response.text}")

        return response.json().get('id')

    def publish_post_from_s3(self, article_id, article_type, date_str, content):
        image_list = self.s3.get_article_images(article_id, article_type, date_str)
        # 2. 각 이미지에 대한 캐러셀 아이템 생성
        carousel_items = []
        for image in image_list:
            image_url = image.get("url")
            if image_url:
                item_id = self.create_carousel_item(image_url)
                carousel_items.append(item_id)
                time.sleep(1)
        if not carousel_items:
            raise Exception("No valid images found")
        content = f"{content} {self.base_content}"
        container_id = self.create_carousel_container(content, carousel_items)
        time.sleep(1)
        post_id = self.publish_carousel(container_id)
        self.logger.info(f"Successfully published carousel post with ID: {post_id}")
        return post_id
