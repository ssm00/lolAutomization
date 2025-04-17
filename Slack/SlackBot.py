import sys
import os
from datetime import datetime
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from MyMetaData.metadata import MetaData
from Instagram.instagram_uploader import InstagramUploader
from Aws.s3 import S3Manager
from util.logger import LogManager, LogType

class SlackBot:
    def __init__(self, account_info, instagram_uploader, logger):
        # Slack Bolt, WebClient, SocketMode 설정
        self.app = App(token=account_info['slack']['slack_bot_token'])
        self.slack_client = WebClient(token=account_info['slack']['slack_bot_token'])
        self.socket_handler = SocketModeHandler(
            self.app,
            account_info['slack']['socket_mode_token']
        )

        self.instagram_uploader = instagram_uploader
        self.logger = logger
        self.instagram_upload_channel_id = account_info['slack']['instagram_upload_channel_id']
        self.s3_manager = S3Manager()
        self.setup_handlers()

    def setup_handlers(self):
        @self.app.event("app_mention")
        def handle_mention(event, say):
            text = event.get("text", "").lower()
            if "upload" in text or "업로드" in text:
                say("인스타그램 업로드를 시작합니다. 날짜를 선택해주세요.")
                self.send_date_select()

        @self.app.action("select_date")
        def handle_date_selection(ack, body):
            ack()
            raw_date = body["actions"][0]["selected_date"]
            formatted_date = datetime.strptime(raw_date, '%Y-%m-%d').strftime('%y_%m_%d')

            articles = self._get_articles(formatted_date)
            if articles:
                self.send_article_select(articles, body["channel"]["id"] )
            else:
                self.slack_client.chat_postMessage(
                    channel=self.instagram_upload_channel_id,
                    text=f"{raw_date} ({formatted_date}) 에 업로드할 article_id가 없습니다."
                )

        # 3) article 선택 → 업로드 확인 메시지
        @self.app.action("select_article")
        def handle_article_selection(ack, body):
            ack()
            payload = json.loads(body["actions"][0]["selected_option"]["value"])
            article_type = payload["article_type"]
            article_id   = payload["article_id"]
            date_str     = payload["date"]

            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text":
                        f"*{article_type}/{article_id}* 을(를) 업로드하시겠습니까?"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "업로드"},
                            "style": "primary",
                            "value": json.dumps(payload),
                            "action_id": "confirm_upload"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "취소"},
                            "style": "danger",
                            "action_id": "cancel_upload"
                        }
                    ]
                }
            ]
            self.slack_client.chat_postMessage(
                channel=body["channel"]["id"],
                blocks=blocks,
                text="업로드 확인"
            )

        @self.app.action("confirm_upload")
        def handle_upload(ack, body):
            ack()
            payload      = json.loads(body["actions"][0]["value"])
            article_type = payload["article_type"]
            article_id   = payload["article_id"]
            date_str     = payload["date"]

            # 캡션 설정 (필요에 따라 수정)
            caption = f"{article_type} {article_id} 업로드"
            post_id = self.instagram_uploader.publish_post_from_s3(
                article_id,
                article_type,
                date_str,
                caption
            )

            if post_id:
                self.slack_client.chat_postMessage(
                    channel=self.instagram_upload_channel_id,
                    text=f"✅ `{article_type}/{article_id}` 포스팅 성공 (post_id: {post_id})"
                )
            else:
                self.slack_client.chat_postMessage(
                    channel=self.instagram_upload_channel_id,
                    text=f"❌ `{article_type}/{article_id}` 포스팅 실패"
                )

        @self.app.action("cancel_upload")
        def handle_cancel(ack, body):
            ack()
            self.slack_client.chat_postMessage(
                channel=body["channel"]["id"],
                text="업로드가 취소되었습니다."
            )

    def send_date_select(self):
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "날짜를 선택해주세요:"}},
            {"type": "actions", "elements": [
                {"type": "datepicker", "action_id": "select_date",
                 "placeholder": {"type": "plain_text", "text": "날짜 선택"}}
            ]}
        ]
        self.slack_client.chat_postMessage(
            channel=self.instagram_upload_channel_id,
            blocks=blocks,
            text="날짜 선택"
        )

    def send_article_select(self, articles, channel_id):
        options = [
            {
                "text": {"type": "plain_text", "text": f"{a['article_type']}/{a['article_id']}"},
                "value": json.dumps(a)
            }
            for a in articles
        ]
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn",
               "text": "업로드할 Article ID 를 선택하세요:"}},
            {"type": "actions", "elements": [
                {"type":      "static_select",
                 "action_id": "select_article",
                 "placeholder": {"type": "plain_text", "text": "Article ID 선택"},
                 "options":   options
                }
            ]}
        ]
        self.slack_client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text="Article ID 선택"
        )

    def _get_articles(self, formatted_date):
        pairs = set()
        for article_type in ["Interview", "MatchResult", "PickRate"]:
            prefix = f"{article_type}/{formatted_date}/"
            resp = self.s3_manager.s3.list_objects_v2(
                Bucket=self.s3_manager.bucket,
                Prefix=prefix
            )
            if 'Contents' not in resp:
                continue
            for obj in resp['Contents']:
                parts = obj['Key'].split('/')
                if len(parts) >= 3:
                    pairs.add((article_type, parts[2]))

        return [
            {"article_type": t, "article_id": aid, "date": formatted_date}
            for t, aid in sorted(pairs)
        ]

    def start(self):
        self.socket_handler.start()

    def stop(self):
        self.socket_handler.close()

def start_slack_bot(logger):
    meta_data = MetaData()
    instagram_uploader = InstagramUploader(meta_data.account_info, logger)
    slack_bot = SlackBot(
        meta_data.account_info,
        instagram_uploader,
        logger
    )
    slack_bot.start()
    return slack_bot


def main():
    try:
        log_manager = LogManager("./logs")
        logger = log_manager.get_logger("main", LogType.SLACK_BOT)
        bot  = start_slack_bot(logger)
        logger.info("SLACK BOT 실행")
    except (KeyboardInterrupt, SystemExit):
        logger.info("SLACK BOT 종료")
    except Exception as e:
        logger.error(f"SLACK BOT 에러: {e}")
    finally:
        bot.stop()

if __name__ == "__main__":
    main()