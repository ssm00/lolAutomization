create table league_info(
	seq int auto_increment primary key,
    official_site_name varchar(100),
	official_site_slug varchar(100) unique,
    official_site_id varchar(100),
    region varchar(30),
	oracle_elixir_name varchar(100),
    image_path text
);
select * from league_info;