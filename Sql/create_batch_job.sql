CREATE TABLE batch_jobs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    start_time datetime,
    end_time datetime,
    duration decimal(10,3),
    error_message text,
    formatted_duration varchar(30),
    INDEX start_time (start_time)
);
