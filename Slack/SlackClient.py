from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime

class SlackClient:

    def __init__(self, database, account_info, s3_manager, logger):
        self.database = database
        self.logger = logger
        self.account_info = account_info
        self.instagram_upload_channel_id = account_info.get('slack').get("instagram_upload_channel_id")
        self.interview_channel_id = account_info.get('slack').get("interview_channel_id")
        self.match_result_channel_id = account_info.get('slack').get("match_result_channel_id")
        self.pick_rate_channel_id = account_info.get('slack').get("pick_rate_channel_id")
        self.slack_client = WebClient(token=account_info.get('slack').get("slack_bot_token"))
        self.s3_manager = s3_manager

    def show_image_list(self, today_images):
        channel_mapping = {
            "Interview": self.interview_channel_id,
            "MatchResult": self.match_result_channel_id,
            "PickRate": self.pick_rate_channel_id
        }
        for category, article_map in today_images.items():
            if category not in channel_mapping:
                self.logger.warning(f"지원되지 않는 카테고리: {category}")
                continue

            channel_id = channel_mapping[category]

            for article_id, file_list in article_map.items():
                try:
                    blocks = [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Article ID:* `{article_id}`"
                            }
                        }
                    ]

                    for file_info in file_list:
                        blocks.append({
                            "type": "image",
                            "image_url": file_info['url'],
                            "alt_text": file_info['name']
                        })
                    self.slack_client.chat_postMessage(
                        channel=channel_id,
                        blocks=blocks,
                        text=f"Images for article {article_id}"
                    )
                except SlackApiError as e:
                    self.logger.error(f"Slack API 오류 발생: {str(e)}")
                except Exception as e:
                    self.logger.error(f"Slack 메시지 전송 중 오류: {str(e)}")