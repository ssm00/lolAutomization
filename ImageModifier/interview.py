from ImageModifier.image_utils import BaseContentProcessor
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import cv2

class Interview(BaseContentProcessor):

    def __init__(self, database, mongo_db, meta_data, article_generator):
        super().__init__(database, meta_data)
        self.database = database
        self.mongo_db = mongo_db
        self.meta_data = meta_data
        self.properties = meta_data.image_modifier_info

        #path
        self.title_background_dir = Path(__file__).parent.parent / "Assets" / "Interview" / "title.png"
        self.main_background_dir = Path(__file__).parent.parent / "Assets" / "Interview" / "main.png"
        self.line_dir = Path(__file__).parent.parent / "Assets" / "Interview" / "line.png"
        self.video_assets_dir = Path(__file__).parent.parent / "Assets" / "Video"
        self.output_dir = Path(__file__).parent.parent / "ImageOutput" / "Interview"

        # properties
        self.title_font_size = self.properties.get("title_font_size")
        self.article_generator = article_generator

    def summary_interview(self, video_path):
        document = self.mongo_db.find_by_video_path(video_path)
        result = self.article_generator.generate_interview_summary(document)
        self.mongo_db.save_interview_summary(result, video_path)

    def extract_thumbnail(self, video_path, frame_number=None):
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

    def title_page(self, video_path):
        #썸네일 생성 및 붙이기
        background = Image.open(self.title_background_dir)
        thumbnail_path = self.extract_thumbnail(video_path)
        thumbnail = Image.open(thumbnail_path)
        thumbnail = self.resize_image(thumbnail, 900, 720)
        background.paste(thumbnail,(91, 231))
        
        #제목
        document = self.mongo_db.find_by_video_path(video_path)
        self.add_first_page_title(background, document['summary']['main_title'])
        self.save_image(background, video_path, "1")

    def main_page(self, video_path):
        document = self.mongo_db.find_by_video_path(video_path)
        summaries = document['summary']['summaries']
        line_image = Image.open(self.line_dir)
        total_pages = (len(summaries) + 2) // 3

        # 각 페이지 생성
        for page_num in range(total_pages):
            background = Image.open(self.main_background_dir)
            draw = ImageDraw.Draw(background)

            start_idx = page_num * 3
            end_idx = min(start_idx + 3, len(summaries))
            page_summaries = summaries[start_idx:end_idx]

            # 각 항목 표시
            x = 91
            y = 231
            subtitle_spacing = 50
            main_content_spacing = 80
            for i, summary in enumerate(page_summaries):
                subtitle = summary['subtitle']
                content = summary['content']
                item_number = start_idx + i + 1

                # 제목 그리기
                subtitle_height = self.draw_subtitle(draw, f"{item_number}. {subtitle}", x, y)
                y += subtitle_height + subtitle_spacing  # 제목과 내용 사이 간격

                background.paste(line_image, (x, y-15), )

                # 내용 그리기
                content_height = self.draw_content(draw, content, x, y)
                y += content_height + main_content_spacing  # 다음 항목과의 간격

            # 이미지 저장
            page_number = page_num + 2  # 첫 페이지가 2부터 시작
            self.save_image(background, video_path, f"{page_number}")

    def draw_subtitle(self, draw, subtitle_text, x, y):
        text_box_width = 900
        title_font_size = 50
        min_title_font_size = 40

        while title_font_size >= min_title_font_size:
            title_font = ImageFont.truetype(self.noto_font_bold_path, title_font_size)
            title_bbox = draw.textbbox((0, 0), subtitle_text, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]

            if title_width <= text_box_width:
                break

            title_font_size -= 2

        if title_font_size < min_title_font_size:
            title_font_size = min_title_font_size
            title_font = ImageFont.truetype(self.noto_font_bold_path, title_font_size)

        draw.text((x, y), subtitle_text, font=title_font, fill="#C89B3C")
        title_bbox = draw.textbbox((0, 0), subtitle_text, font=title_font)
        return title_bbox[3] - title_bbox[1]

    def draw_content(self, draw, content, x, y):
        text_box_width = 900
        content_font = ImageFont.truetype(self.noto_font_bold_path, 40)

        # 텍스트를 여러 줄로 분할
        words = content.split()
        lines = []
        current_line = []

        for word in words:
            test_line = current_line + [word]
            test_text = " ".join(test_line)
            content_bbox = draw.textbbox((0, 0), test_text, font=content_font)
            content_width = content_bbox[2] - content_bbox[0]

            if content_width <= text_box_width:
                current_line = test_line
            else:
                lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        initial_y = y

        for line in lines:
            draw.text((x, y), line, font=content_font, fill="#FFFFFF")  # 흰색 텍스트
            line_bbox = draw.textbbox((0, 0), line, font=content_font)
            line_height = line_bbox[3] - line_bbox[1]
            y += line_height + 5  # 줄 간 약간의 간격

        return y - initial_y
