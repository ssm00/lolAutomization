import yt_dlp
import json
import time
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


class DownloadFailedException(Exception):

    def __init__(self, index, message="다운로드 실패", retry_count=0):
        self.index = index
        self.retry_count = retry_count
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (인덱스: {self.index}, 재시도: {self.retry_count}회)"


class LCKOfficial:
    def __init__(self, mongo=None):
        self.channel_url = "https://www.youtube.com/channel/UCw1DsweY9b2AKGjV4kGJP1A/videos"
        self.mongo = mongo
        current_path = Path(__file__).resolve()
        self.output_dir = current_path.parent.parent.parent / "Assets" / "Video" / "lck"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_channel_videos(self, batch_size=10, start_index=1):
        """채널에서 영상 목록 가져오기"""
        ydl_opts = {
            'ignoreerrors': True,
            'extract_flat': False,  # 상세 메타데이터 가져오기 위해 False로 설정
            'quiet': False,
            'no_warnings': True,
            'playlistreverse': False,  # 최신 영상부터 가져오기
            'playliststart': start_index,  # 시작 인덱스
            'playlistend': start_index + batch_size - 1,  # 종료 인덱스
            'skip_download': True,  # 실제 영상은 다운로드하지 않음
            'socket_timeout': 30,  # 소켓 타임아웃 증가
        }

        print(f"영상 정보 가져오기: {start_index}번부터 {start_index + batch_size - 1}번까지")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.channel_url, download=False)
                videos = []

                if not info or 'entries' not in info:
                    print(f"채널 정보를 가져오는데 문제가 발생했습니다. 응답: {info}")
                    return videos

                entries = info.get('entries', [])
                if not entries:
                    print("더 이상 가져올 영상이 없습니다.")
                    return videos

                print(f"총 {len(entries)}개의 영상 정보를 가져왔습니다.")

                for entry in entries:
                    if entry and 'id' in entry:
                        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                        video_title = entry.get('title', 'No title')

                        # 업로드 날짜 형식 변환 (YYYYMMDD)
                        upload_date = entry.get('upload_date', 'Unknown')
                        if upload_date and upload_date != 'Unknown':
                            # YYYYMMDD 형식 확인
                            if len(upload_date) == 8 and upload_date.isdigit():
                                formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
                            else:
                                formatted_date = upload_date
                        else:
                            formatted_date = 'Unknown'

                        # 디버깅을 위한 출력
                        print(f"영상 ID: {entry['id']}, 제목: {video_title}, 업로드일: {upload_date} ({formatted_date})")

                        # 추가 메타데이터 수집
                        video_data = {
                            'id': entry['id'],
                            'title': video_title,
                            'url': video_url,
                            'upload_date': upload_date,
                            'formatted_date': formatted_date
                        }
                        for key in ['duration', 'view_count', 'like_count', 'comment_count', 'description']:
                            if key in entry:
                                video_data[key] = entry[key]

                        videos.append(video_data)

                return videos
        except Exception as e:
            print(f"영상 정보 가져오기 중 오류 발생: {str(e)}")
            return []

    def download_video(self, video_url, video_idx=None, retry_count=0, max_retries=3):
        file_path = None

        def my_hook(d):
            nonlocal file_path
            if d['status'] == 'finished':
                file_path = Path(d['filename'])
                print(f"다운로드 완료: {file_path}")
                print("후처리 중...")

        ydl_opts = {
            'format': 'best',
            'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),  # Path 객체를 문자열로 변환
            'quiet': False,
            'progress': True,  # 진행 상황 표시
            'nooverwrites': True,  # 이미 존재하는 파일은 덮어쓰지 않음
            'retries': 5,  # 기본 재시도 횟수
            'fragment_retries': 10,  # 세그먼트 다운로드 실패시 재시도 횟수
            'socket_timeout': 60,  # 소켓 타임아웃 시간
            'extractor_retries': 5,  # 정보 추출 실패시 재시도 횟수
            'progress_hooks': [my_hook],  # 진행 상황 훅
        }

        print(f"다운로드 경로: {self.output_dir}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            if file_path is None:
                print("경고: 다운로드는 성공했으나 파일 경로를 확인할 수 없습니다.")
                files = list(self.output_dir.glob('*'))
                if files:
                    file_path = max(files, key=os.path.getctime)
                    print(f"추정된 파일 경로: {file_path}")

            return True, file_path

        except Exception as e:
            error_msg = f"다운로드 중 오류 발생: {str(e)}"
            print(f"{error_msg} (시도 {retry_count + 1}/{max_retries})")

            retry_count += 1
            if retry_count < max_retries:
                # 개별 다운로드 재시도 로직
                wait_time = retry_count * 5
                print(f"{wait_time}초 후 재시도합니다...")
                time.sleep(wait_time)
                return self.download_video(video_url, video_idx, retry_count, max_retries)
            else:
                # 최대 재시도 횟수 초과 시 예외 발생
                if video_idx is not None:
                    raise DownloadFailedException(video_idx, f"영상 다운로드 실패: {str(e)}", retry_count)
                return False, None

    def save_video_metadata_to_mongodb(self, video_data, file_path=None):
        metadata = {
            "video_id": video_data['id'],
            "title": video_data['title'],
            "url": video_data['url'],
            "upload_date": video_data['upload_date'],
            "downloaded_at": datetime.now(),
            "video_path": str(file_path) if file_path else None,
        }

        for key in ['duration', 'view_count', 'like_count', 'comment_count', 'description']:
            if key in video_data:
                metadata[key] = video_data[key]

        self.mongo.save_lck_video_metadata(metadata)
        return True

    def download_videos_by_date(self, days=1, max_retries=3, batch_size=10, max_batches=10, start_idx=0):
        today = datetime.now()
        end_date = today
        start_date = today - timedelta(days=days)
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        print(f"다운로드 날짜 범위: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        try:
            total_valid_videos = []
            current_batch = 1
            start_index = 1
            range_exceeded = False
            while not range_exceeded and current_batch <= max_batches:
                retries = 0
                while retries < max_retries:
                    try:
                        videos = self.get_channel_videos(batch_size=batch_size, start_index=start_index)
                        if not videos:
                            print("채널에서 더 이상 영상을 가져올 수 없습니다.")
                            break

                        all_in_range = True
                        batch_valid_videos = []
                        for video in videos:
                            upload_date = video.get('upload_date', '00000000')
                            if start_date_str <= upload_date <= end_date_str:
                                batch_valid_videos.append(video)
                                print(f"포함됨: {video['title']} (업로드일: {upload_date})")
                            else:
                                print(
                                    f"제외됨: {video['title']} (업로드일: {upload_date}, 범위: {start_date_str} ~ {end_date_str})")
                                all_in_range = False
                                range_exceeded = True

                        total_valid_videos.extend(batch_valid_videos)
                        print(f"현재까지 찾은 유효 영상 수: {len(total_valid_videos)}")

                        # 더 이상 영상이 없거나 날짜 범위를 벗어난 영상이 발견되면 종료
                        if not videos or range_exceeded:
                            if range_exceeded:
                                print("날짜 범위를 벗어난 영상이 발견되어 검색을 중단합니다.")
                            break

                        # 배치의 모든 영상이 범위 내에 있다면 다음 배치로 이동
                        if all_in_range:
                            start_index += batch_size
                            current_batch += 1
                            print("현재 배치의 모든 영상이 날짜 범위 내에 있습니다. 다음 배치를 확인합니다.")

                        break

                    except Exception as e:
                        retries += 1
                        print(f"오류 발생: {str(e)}")
                        if retries < max_retries:
                            print(f"재시도 {retries}/{max_retries}...")
                            time.sleep(5)
                        else:
                            print(f"배치 {current_batch} 처리 중 최대 재시도 횟수를 초과했습니다.")

            return self._download_video_batch(total_valid_videos, max_retries, start_idx)

        except Exception as e:
            print(f"전체 과정 중 오류 발생: {str(e)}")
            return 0

    def _download_video_batch(self, videos, max_retries=3, start_idx=0, global_retries=0):
        if global_retries >= max_retries:
            print(f"전체 다운로드 최대 재시도 횟수({max_retries}회)를 초과했습니다.")
            return 0
        download_completed = 0
        try:
            for idx in range(start_idx, len(videos)):
                video = videos[idx]
                try:
                    print(f"\n[{idx + 1}/{len(videos)}] 제목: {video['title']}")
                    print(f"URL: {video['url']}")
                    print(f"업로드일: {video.get('upload_date', 'Unknown')}")
                    if self.mongo.find_lck_video_by_id(video['id']):
                        print(f"{video['title']} 이미 다운로드되어 있습니다. 다음 영상으로 진행합니다.")
                        continue

                    print("다운로드 중...")
                    success, file_path = self.download_video(video['url'], idx)

                    if success:
                        self.save_video_metadata_to_mongodb(video, file_path)
                        download_completed += 1
                        print(f"{video['title']} 다운로드 완료!")
                    else:
                        print(f"{video['title']} 다운로드 실패.")
                        raise DownloadFailedException(idx, "다운로드 실패")

                except DownloadFailedException as e:
                    print(f"다운로드 중단 지점: {e}")
                    if global_retries < max_retries - 1:
                        # 대기 후 실패한 인덱스부터 재시도
                        wait_time = (global_retries + 1) * 15
                        print(f"{wait_time}초 후 인덱스 {idx}부터 다시 시도합니다...")
                        time.sleep(wait_time)

                        # 현재 인덱스부터 재귀적으로 다시 시도 (재시도 카운트 증가)
                        additional_completed = self._download_video_batch(
                            videos, max_retries, idx, global_retries + 1
                        )
                        return download_completed + additional_completed
                    else:
                        print(f"최대 재시도 횟수({max_retries}회)를 초과했습니다. 다음 영상으로 진행합니다.")
                        continue

                except Exception as e:
                    print(f"예상치 못한 오류 발생: {str(e)}")
                    raise DownloadFailedException(idx, f"예상치 못한 오류: {str(e)}")
            print("\n모든 영상 다운로드가 완료되었습니다!")
            return download_completed

        except Exception as e:
            print(f"배치 다운로드 중 치명적 오류 발생: {str(e)}")

            if global_retries < max_retries - 1:
                wait_time = (global_retries + 1) * 20
                print(f"{wait_time}초 후 현재 인덱스({start_idx})부터 다시 시도합니다...")
                time.sleep(wait_time)

                additional_completed = self._download_video_batch(
                    videos, max_retries, start_idx, global_retries + 1
                )
                return download_completed + additional_completed
            else:
                print("최대 재시도 횟수를 초과했습니다. 다운로드를 중단합니다.")
                return download_completed

