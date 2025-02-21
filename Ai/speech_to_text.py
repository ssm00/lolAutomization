import whisper
import time
import torch
from Db import mongo_db
from MyMetaData import metadata
from text_refiner import TextRefiner

def transcribe_video(video_path, model_size="large", language="ko"):
    try:
        print(f"GPU 사용 가능 여부: {torch.cuda.is_available()}")

        print(f"모델 로딩 중... ({model_size})")
        start_time = time.time()

        model = whisper.load_model(model_size)

        print(f"모델 로딩 완료! (소요시간: {time.time() - start_time:.1f}초)")
        print("음성을 텍스트로 변환 중...")

        # 음성을 텍스트로 변환
        start_time = time.time()
        result = model.transcribe(
            video_path,
            language=language,
            verbose=True,
            initial_prompt="안녕하세요. 한국어 음성을 텍스트로 변환합니다."
        )

        print(f"변환 완료! (소요시간: {time.time() - start_time:.1f}초)")
        print(result)
        return result

    except Exception as e:
        print(f"에러 발생: {str(e)}")
        return None


def save_transcript(result, output_path, save_segments=True):

    try:
        if result is None:
            print("저장할 결과가 없습니다.")
            return

        # 전체 텍스트 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            # 전체 텍스트
            f.write("[전체 텍스트]\n")
            f.write(result["text"])
            f.write("\n\n")

            # 세그먼트 별 정보 저장
            if save_segments:
                f.write("[세그먼트 별 정보]\n")
                for segment in result["segments"]:
                    start_time = time.strftime('%H:%M:%S', time.gmtime(segment["start"]))
                    end_time = time.strftime('%H:%M:%S', time.gmtime(segment["end"]))
                    f.write(f"\n[{start_time} -> {end_time}]\n")
                    f.write(f"{segment['text'].strip()}\n")

        database.save_transcription(result, VIDEO_PATH)
        print(f"결과가 {output_path}에 저장되었습니다.")

    except Exception as e:
        print(f"결과 저장 중 에러 발생: {str(e)}")


if __name__ == "__main__":
    # 설정
    VIDEO_PATH = "../input.mp4"
    OUTPUT_PATH = "output_whisper.txt"
    MODEL_SIZE = "small"  # tiny, base, small, medium, large 중 선택
    LANGUAGE = "ko"  # 한국어

    meta = metadata.MetaData()
    mongo_info = meta.db_info['mongo_local']
    database = mongo_db.MongoDB(mongo_info)
    # # 실행
    # result = transcribe_video(VIDEO_PATH, MODEL_SIZE, LANGUAGE)
    # if result:
    #     save_transcript(result, OUTPUT_PATH)

    document = database.find_by_video_path(VIDEO_PATH)

    # 텍스트 개선
    refiner = TextRefiner()
    refined_result = refiner.refine_interview(document)
    print(refined_result)

