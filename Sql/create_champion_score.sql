create table champion_score_mid(
	seq int auto_increment primary key,
    name_us varchar(50),
    name_kr varchar(50),
    champion_tier int,
    ranking int,
    ranking_variation int,
    is_op boolean,
    ps_score decimal(5,2),
    honey_score decimal(5,2),
    win_rate decimal(4,2),
    pick_rate decimal(4,2),
    ban_rate decimal(4,2),
    sample_size int,
    patch decimal(4,2),
    survey_target_tier varchar(20),
    region varchar(20),
    updated_at datetime,
    unique key unique_patch_champ (patch, name_us)
);
drop table champion_score_top;
drop table champion_score_mid;
drop table champion_score_jungle;
drop table champion_score_bottom;
drop table champion_score_support;
drop table champion_score_all;
select * from champion_score_mid;

select * from champion_score_top where patch = (select max(patch) from champion_score_top);

