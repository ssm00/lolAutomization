import threading
import time
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from multiprocessing import Process, freeze_support
from urllib.parse import quote_plus
from apscheduler.triggers.date import DateTrigger

from Db import jobDb
from Db.mongo_db import MongoDB
from Db.mysql_db import Database
from MyMetaData.metadata import MetaData
from main import Main
from util.logger import LogManager, LogType
import traceback

from apscheduler.events import EVENT_SCHEDULER_STARTED, EVENT_SCHEDULER_SHUTDOWN, EVENT_JOB_ERROR, EVENT_JOB_EXECUTED


class JobExecutor:

    def __init__(self, meta_data, log_manager):
        self.meta_data = meta_data
        self.log_manager = log_manager
        self.logger = log_manager.get_logger("job_executor", LogType.BATCH)
        self.job_db = None

    def creat_job_db(self):
        return jobDb.Database(self.meta_data.db_info.get("mysql"), self.logger)

    def stop_running_jobs(self):
        try:
            if not self.job_db:
                self.job_db = self.creat_job_db()
            running_jobs = self.job_db.get_all_running_job()
            end_time = datetime.now()
            for job in running_jobs:
                duration = (end_time - job.get("start_time")).total_seconds()
                formatted_duration = self.format_duration(duration)
                self.job_db.stop_job(job.get("id"), end_time, duration, formatted_duration)
        except Exception as e:
            self.logger.error(f"실행 중인 작업 상태 업데이트 실패: {str(e)} {traceback.format_exc()}")
        finally:
            if self.job_db:
                self.job_db.close()

    def format_duration(self, duration_seconds):
        if duration_seconds is None:
            return "알 수 없음"
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = duration_seconds % 60
        parts = []
        if hours > 0:
            parts.append(f"{hours}시간")
        if minutes > 0:
            parts.append(f"{minutes}분")
        if seconds > 0 or not parts:
            parts.append(f"{seconds:.3f}초")
        return " ".join(parts)

    def execute_daily_work(self):
        start_time = datetime.now()
        self.job_db = self.creat_job_db()
        try:
            job_id = self.job_db.create_job("LOL 일일 기사 생성")
            daily_work_logger = self.log_manager.get_logger("daily_work_logger", LogType.PROGRAM)
            mysql_logger = self.log_manager.get_logger("mysql_logger", LogType.PROGRAM)
            mysql = Database(self.meta_data.db_info["mysql"], self.meta_data, logger=mysql_logger)
            mongo = MongoDB(self.meta_data.db_info["mysql"])
            try:
                lol_main = Main(mysql, mongo, self.meta_data, daily_work_logger)
                lol_main.daily_work()
                status = 'SUCCESS'
                error_msg = None
            except Exception as e:
                status = 'FAILED'
                error_msg = str(e)
                raise
            finally:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                formatted_duration = self.format_duration(duration)
                self.job_db.update_job_status(job_id, status, duration, formatted_duration, end_time, error_msg)
                mysql.close()

        except Exception as e:
            self.logger.error(f"LOL 일일 기사 생성 작업 실패: {str(e)}")
            raise
        finally:
            if self.job_db:
                self.job_db.close()


class Scheduler:

    def __init__(self, meta_data, log_manager):
        self.meta_data = meta_data
        self.log_manager = log_manager
        self.scheduler_logger = self.log_manager.get_logger("scheduler", LogType.BATCH)
        self.job_executor = JobExecutor(meta_data, self.log_manager)
        self.scheduler = self._init_scheduler()

    def _init_scheduler(self):
        scheduler_info = self.meta_data.scheduler_info
        mysql_info = self.meta_data.db_info.get("mysql")
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=f"""mysql+pymysql://{mysql_info.get("id")}:{quote_plus(mysql_info.get("password"))}@{mysql_info.get("host")}:{mysql_info.get("port")}/{mysql_info.get("db")}""",
                engine_options={
                    'pool_recycle': 3600,
                    'pool_pre_ping': True,
                    'pool_size': 5,
                    'max_overflow': 10
                }

            )
        }

        executors = {
            'default': ThreadPoolExecutor(scheduler_info.get("max_threads")),
            'processpool': ProcessPoolExecutor(scheduler_info.get("max_processes"))
        }

        scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            timezone='Asia/Seoul',
            daemon=False
        )
        return scheduler


    def add_jobs(self):
        self.scheduler.add_job(
            self.job_executor.execute_daily_work,
            #trigger=CronTrigger(hour=self.meta_data.scheduler_info['jobs']['daily_f1_work']['schedule']['hour'], minute=self.meta_data.scheduler_info['jobs']['daily_f1_work']['schedule']['minute']),
            trigger=DateTrigger(run_date=datetime.now()),
            id='lol_daily_job',
            name='lol_daily_job',
            replace_existing=True,
        )
        self.scheduler_logger.info("LOL JOB 추가")

    def start(self):
        try:
            self.add_jobs()
            self.scheduler.start()
            self.scheduler_logger.info("스케줄러가 시작되었습니다.")
        except Exception as e:
            self.scheduler_logger.error(f"스케줄러 시작 실패: {e}")
            raise

    def shutdown(self):
        self.job_executor.stop_running_jobs()
        self.scheduler.shutdown()
        self.scheduler_logger.info("스케줄러가 종료되었습니다.")

def main():
    try:
        log_manager = LogManager(Path(__file__).parent / "logs")
        main_logger = log_manager.get_logger("main", LogType.BATCH)
        meta_data = MetaData()
        scheduler = Scheduler(meta_data, log_manager)
        scheduler.start()

        try:
            while True:
                time.sleep(10)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
        except Exception as e:
            main_logger.error(f"스케줄러 메인 루프에서 오류 발생: {e} {traceback.format_exc()}")

    except Exception as e:
        main_logger.error(f"프로그램 실행 중 오류 발생: {traceback.format_exc()}")

if __name__ == '__main__':
    freeze_support()
    main()
