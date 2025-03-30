from pathlib import Path

import MyMetaData.metadata
from Db.mongo_db import MongoDB
import cv2
import os
import random
import requests
from PIL import Image
from dotenv import load_dotenv
import base64


class ThumbnailSelector:

    def __init__(self, mongo_db, api_url=None):
        load_dotenv()
        self.mongo_db = mongo_db
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.api_url = api_url or "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-4o"
        current_path = Path(__file__).resolve()
        self.output_dir = current_path.parent.parent.parent / "Assets" / "Video" / "lck" / "capture"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.criteria = {
            "visual_quality": 0.2,
            "title_relevance": 0.3,
            "object_representation": 0.2,  # 중요 객체 표현
            "emotional_impact": 0.15,  # 감성적 임팩트
            "clickbait_potential": 0.15  # 클릭 유도성
        }

    def capture_random_frames(self, video_path, num_frames=5):
        try:
            cap = cv2.VideoCapture(video_path)
            video_info = self.mongo_db.find_lcK_video_by_video_path(video_path)
            video_id = video_info['_id']
            if not cap.isOpened():
                print(f"비디오를 열 수 없습니다: {video_path}")
                return None
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0

            # 너무 짧은 영상인 경우 처리
            if total_frames <= num_frames:
                frame_indices = list(range(total_frames))
            else:
                start_frame = int(5 * fps) if duration > 10 else 0
                end_frame = total_frames - int(5 * fps) if duration > 10 else total_frames
                frame_indices = sorted(random.sample(range(start_frame, end_frame), num_frames))

            # 프레임 캡처
            captured_frames = []
            frame_paths = []

            for i, frame_idx in enumerate(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()

                if ret:
                    frame_path = os.path.join(self.output_dir, f"{video_id}_{i}.jpg")
                    cv2.imwrite(frame_path, frame)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(rgb_frame)
                    captured_frames.append(pil_image)
                    frame_paths.append(frame_path)
                    print(f"프레임 캡처 완료: {frame_path} (인덱스: {frame_idx})")
            cap.release()
            return {
                "frames": captured_frames,
                "frame_paths": frame_paths,
                "video_path": video_path,
                "total_frames": total_frames,
                "duration": duration
            }

        except Exception as e:
            print(f"프레임 캡처 중 오류 발생: {str(e)}")
            return None

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def evaluate_image(self, image_path, video_title):
        base64_image = self.encode_image(image_path)
        prompt = f"""
            이 이미지를 "{video_title}"이라는
            제목의 영상 썸네일로 평가해주세요. 다음 기준에 따라 1-10점 사이의 점수를 매겨주세요:
    
            1. 시각적 품질: 이미지의 선명도, 밝기, 색상 대비 (1-10)
            2. 제목 관련성: 영상 제목과의 관련성 (1-10)
            3. 인물/객체 표현: 중요 인물이나 객체의 표현 품질 (1-10)
            4. 감정적 영향력: 감정이나 흥미 유발 정도 (1-10)
            5. 클릭 유도성: 시청자의 클릭을 유도할 가능성 (1-10)
    
            점수만 간결하게 아래 JSON 형식으로 응답해주세요:
            {{
                "visual_quality": 점수,
                "title_relevance": 점수,
                "object_representation": 점수,
                "emotional_impact": 점수,
                "clickbait_potential": 점수
            }}
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }
        response = requests.post(self.api_url, headers=headers, json=payload)
        response_data = response.json()
        # 응답 처리
        if 'choices' in response_data and len(response_data['choices']) > 0:
            content = response_data['choices'][0]['message']['content']

            # JSON 추출
            import json
            import re

            # JSON 형식의 텍스트 찾기
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                json_str = json_match.group(0)
                scores = json.loads(json_str)
                return scores

            print(f"API 응답에서 JSON을 추출할 수 없습니다: {content}")
            return None

        print(f"API 응답 구조가 예상과 다릅니다: {response_data}")
        return None


    def calculate_final_score(self, criteria_scores):
        if not criteria_scores:
            return 0

        final_score = sum(criteria_scores.get(criterion, 0) * weight
                          for criterion, weight in self.criteria.items())
        return final_score

    def select_by_vlm(self, frame_data, video_info):
        best_thumbnail = None
        best_score = -1
        all_evaluations = []

        for i, frame_path in enumerate(frame_data["frame_paths"]):
            print(f"프레임 {i + 1}/{len(frame_data['frame_paths'])} 평가 중...")
            criteria_scores = self.evaluate_image(frame_path, video_info['title'])
            if criteria_scores:
                final_score = self.calculate_final_score(criteria_scores)
                evaluation = {
                    "frame_index": i,
                    "path": frame_path,
                    "criteria_scores": criteria_scores,
                    "score": final_score
                }
                all_evaluations.append(evaluation)

                print(f"프레임 {i + 1} 평가 완료 - 점수: {final_score:.2f}")
                if final_score > best_score:
                    best_score = final_score
                    best_thumbnail = evaluation

        if best_thumbnail:
            print(f"최적의 썸네일 선택됨: {best_thumbnail['path']} (점수: {best_thumbnail['score']:.2f})")
            if "video_id" in frame_data:
                self.mongo_db.save_thumbnail_selection(video_info['_id'], best_thumbnail)
        else:
            print("썸네일 선택에 실패했습니다.")

        return best_thumbnail['path']

    def sanitize_filename(self, filename):
        safe_filename = ''.join(c if c.isalnum() or c in ['-', '_', '.'] else '_' for c in filename)
        safe_filename = safe_filename[:50] if len(safe_filename) > 50 else safe_filename
        return safe_filename

    def extract_thumbnail_by_frame(self, video_path, frame_number=None):
        cap = cv2.VideoCapture(self.video_assets_dir / video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_number is None:
            frame_number = total_frames // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            print("프레임을 읽는 데 실패했습니다.")
            return None
        output_path = Path(__file__).parent.parent / "Assets" / "Interview" / "title_image" / f"{video_path}.png"
        if output_path:
            cv2.imwrite(output_path, frame)
        return output_path

    def extract_thumbnail_at_time(self, video_path, output_path=None, time_in_seconds=10):
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_number = int(time_in_seconds * fps)
        # 특정 프레임으로 이동
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()
        if output_path and ret:
            cv2.imwrite(output_path, frame)
        return frame if ret else None

    def evaluate_clip(self, image_list):
        pass

    def run_by_vlm(self, video_path):
        video_info = self.mongo_db.find_lcK_video_by_video_path(video_path)
        frame_data = self.capture_random_frames(video_path, num_frames=5)
        return self.select_by_vlm(frame_data, video_info)

