import openai
import json
import anthropic
from util.commonException import CommonError, ErrorCode


class GenAiAPI:

    def __init__(self, prompt_json, key_json):
        self.prompt = prompt_json
        self.model = key_json.get("model")
        self.version = None
        if self.model =="gpt":
            self.client = openai.OpenAI(api_key=key_json.get("open_ai_api_key"))
            self.version = key_json.get("gpt_version")
        elif self.model == "claude":
            self.client = anthropic.Anthropic(api_key=key_json.get("claude_api_key"))
            self.version = key_json.get("claude_version")

    def get_gpt_translation(self, content):
        completion = self.client.chat.completions.create(
            model=self.version,
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": content}
            ]
        )
        return completion.choices[0].message.content

    def get_claude_translation(self, content):
        # 기본 self.client.messages.create
        # 캐시 사용 비용 40~50프로 절감 굳
        completion = self.client.beta.prompt_caching.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0.0,
            system=[{
                "type": "text",
                "text": self.prompt,
                "cache_control": {"type": "ephemeral"}
            }],
            messages=[{
                "role": "user",
                "content": self.create_prompt(content)
            }]
        )
        return completion.content[0].text

    def handle_malformed_json(self, content):
        print(content)
        start_index = content.find('{')
        if start_index == -1:
            raise CommonError(
                ErrorCode.JSON_DECODE_ERROR,
                "JSON 형식을 찾을 수 없음",
                content
            )
        return json.loads(content[start_index:])

    def parse_json_content(self, raw_content):
        try:
            return json.loads(raw_content)
        except json.decoder.JSONDecodeError:
            return self.handle_malformed_json(raw_content)

    def validate_translation(self, content):
        if not content or not isinstance(content, dict):
            raise CommonError(
                ErrorCode.INVALID_RESPONSE,
                "번역 결과가 올바르지 않은 형식임",
                content
            )

    def api_error(self, error):
        if isinstance(error, anthropic.InternalServerError) and error.status_code == "529":
            raise CommonError(
                ErrorCode.SERVER_BUSY,
                "anthropic 서버 과부화 나중에 일단 넘어감 나중에 다시 시도",
                error
            )
        if isinstance(error, anthropic.BadRequestError):
            raise CommonError(
                ErrorCode.SERVER_BUSY,
                "anthropic 돈 다씀",
                error
            )

    def get_translation(self, content):
        if self.model == "gpt":
            return self.get_gpt_translation(content)
        return self.get_claude_translation(content)

    def translate_v1(self, content):
        try:
            raw_translation = self.get_translation(content)
            parsed_content = self.parse_json_content(raw_translation)
            self.validate_translation(parsed_content)
            return parsed_content
        except (anthropic.InternalServerError, anthropic.BadRequestError) as err:
            self.api_error(err)
        except json.decoder.JSONDecodeError as err:
            raise CommonError(ErrorCode.JSON_DECODE_ERROR, "JSON { 찾아도 디코딩 실패", err)