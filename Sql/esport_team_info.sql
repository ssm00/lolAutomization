create table team_info(
	 seq int auto_increment primary key,
     official_site_id  varchar(100),
	 official_site_name varchar(100),
	 official_site_slug varchar(100) unique,
	 official_site_code varchar(50),
     wins int,
     losses int,
     ties int,
	 image_path text,
     league_seq int,
     oracle_elixir_name varchar(100),
     foreign key (league_seq) references league_info(seq)
);

select * from team_info;

select distinct(teamname), league from oracle_elixir_2025 where teamname not in (select official_site_name from team_info); 
select count(distinct(teamname)) from oracle_elixir_2025 where teamname like "%(select official_site_name from team_info)%";
select distinct(league) from oracle_elixir_2025 as oe where not exists
(select 1 from team_info as ti join league_info as li on li.seq = ti.seq where oe.league = li.official_site_name); 

select teamname from league_info  where league = "";
select * from league_info;
select count(distinct(league)) from oracle_elixir_2025;

SELECT count(official_site_name)
FROM team_info t1
WHERE NOT EXISTS (
    SELECT 1
    FROM oracle_elixir_2025 t2
    WHERE t2.teamname LIKE CONCAT('%', t1.official_site_name, '%')
)