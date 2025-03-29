import whisper
import time
import torch
from pydub import AudioSegment
from openai import OpenAI
import os

class SpeechToText:

    def __init__(self, mongo_db):
        self.mongo_db = mongo_db
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def extract_text_lck_interview_local(self, video_path, model_size="medium", language=None):
        try:
            print(f"GPU 사용 가능 여부: {torch.cuda.is_available()}")
            print(f"모델 로딩 중... ({model_size})")
            start_time = time.time()
            model = whisper.load_model(model_size)
            print(f"모델 로딩 완료! (소요시간: {time.time() - start_time:.1f}초)")
            print("음성을 텍스트로 변환 중...")
            start_time = time.time()
            result = model.transcribe(
                video_path,
                language=language,
                verbose=True,
                initial_prompt="안녕하세요. 한국어 음성을 텍스트로 변환합니다."
            )

            print(f"변환 완료! (소요시간: {time.time() - start_time:.1f}초)")
            return self.mongo_db.save_interview_transcription(result, video_path)
        except Exception as e:
            print(f"에러 발생: {str(e)}")
            return None

    # 4o 분당 0.006
    # 4o-mini 0.003
    # whisper 0.006
    # aws 0.024
    # universal-2 0.002
    # 결과는 4o-mini가 whisper 보다 나아보임 근데 segment 표시 안됨
    def extract_text_lck_interview(self, video_path, model="gpt-4o-mini-transcribe", language=None):
        try:
            print(f"API를 사용하여 음성을 텍스트로 변환 중... (모델: {model})")
            start_time = time.time()
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            if file_size_mb > 25:
                print(f"경고: 파일 크기가 {file_size_mb:.1f}MB로, 25MB 제한을 초과합니다.")
                # self._split_large_audio(audio_path)

            with open(video_path, "rb") as audio_file:
                api_params = {
                    "model": model,
                    "file": audio_file,
                }
                if model == "whisper-1":
                    api_params["response_format"] = "verbose_json"
                else:
                    api_params["response_format"] = "json"
                if language:
                    api_params["language"] = language
                api_params["prompt"] = "안녕하세요. 한국어 음성을 텍스트로 변환합니다."
                result = self.client.audio.transcriptions.create(**api_params)

            print(f"변환 완료! (소요시간: {time.time() - start_time:.1f}초)")
            if hasattr(result, 'model_dump'):
                result_dict = result.model_dump()
            elif hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif hasattr(result, '__dict__'):
                result_dict = vars(result)
            else:
                # 이미 딕셔너리거나 JSON 문자열인 경우
                if isinstance(result, dict):
                    result_dict = result
                elif isinstance(result, str):
                    import json
                    result_dict = json.loads(result)
                else:
                    # 기본 fallback - 문자열 속성 추출 시도
                    result_dict = {"text": str(result)}

            if "segments" not in result_dict and model != "whisper-1":
                result_dict["segments"] = []
            self.mongo_db.save_interview_transcription(result_dict, video_path)
        except Exception as e:
            print(f"에러 발생: {str(e)}")
            return None

    # 필요시 대용량 오디오 파일 분할 메소드 추가
    def _split_large_audio(self, audio_path, chunk_minutes=10):
        try:
            audio = AudioSegment.from_file(audio_path)
            # PyDub는 밀리초 단위로 처리
            chunk_length_ms = chunk_minutes * 60 * 1000
            chunks = []

            # 파일 이름과 확장자 분리
            base_name = os.path.splitext(audio_path)[0]
            extension = os.path.splitext(audio_path)[1]

            # 청크로 분할
            for i, chunk in enumerate(audio[::chunk_length_ms]):
                chunk_name = f"{base_name}_chunk{i}{extension}"
                chunk.export(chunk_name, format=extension.replace(".", ""))
                chunks.append(chunk_name)
                print(f"청크 생성: {chunk_name}")

            return chunks

        except Exception as e:
            print(f"오디오 분할 중 오류 발생: {str(e)}")
            return None