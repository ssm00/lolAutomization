create table patch_info(
	seq int primary key auto_increment,
    patch decimal(4,2) unique key,
    title varchar(255),
    url varchar(255),
    description TEXT,
    patch_date date
    );
drop table patch_info;
select * from patch_info;