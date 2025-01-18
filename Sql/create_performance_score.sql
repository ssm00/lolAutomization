create table performance_score(
	seq int primary key auto_increment,
    name_us varchar(50),
    name_kr varchar(50),
    pick_rate decimal(4,2),
    win_rate decimal(4,2),
    ban_rate decimal(4,2),
    champion_tier int,
    patch decimal(4,2),
    line varchar(30),
    performance_score decimal(4,2),
	anomaly_score decimal(4,2),
    is_outlier boolean,
    unique key unique_champ (patch, name_us, line)
);
drop table performance_score;
select * from performance_score where line = "top";
select name_us, count(name_us) from performance_score group by name_us;
select * from performance_score where name_us = "zac";

select * from oracle_elixir where champion = "Nunu & Willump";
select * from champion_score_top;

SELECT DISTINCT o.champion, p.name_us
FROM oracle_elixir o
LEFT JOIN performance_score p 
    ON o.champion = p.name_us
WHERE p.name_us IS NULL
    AND o.position != 'team'
ORDER BY o.champion;
