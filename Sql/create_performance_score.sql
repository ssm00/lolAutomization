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
    performance_score decimal(5,2),
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
use lol_dev;
select * from oracle_elixir where gameid =  "LOLTMNT02_29804";
select * from oracle_elixir where name_us="Skarner" and playername = "Canyon";
select * from oracle_elixir where game_date between Date(2024-08-16) and playername = "Canyon";
select count(distinct(gameid)) from oracle_elixir where name_us = "Skarner" and position = "jungle" and patch = 14.15;
select count(distinct(gameid)) from oracle_elixir where name_us = "Sejuani" and position = "jungle" and patch = 14.15;

select count(distinct(gameid)) from oracle_elixir where name_us = "Aphelios" and position = "bottom" and patch = 14.15;
select * from oracle_elixir where name_us = "Nilah" and position = "bottom" and patch = 14.15;
select count(distinct(gameid)) from oracle_elixir where position = "jungle" and patch = 14.15;
select name_us, count(name_us) from oracle_elixir where position = "jungle" and patch = 14.15 group by (name_us);
select count(distinct(gameid)) from oracle_elixir where patch = 14.15;
select * from oracle_elixir where name_us = "brand" and position = "jungle" and playername = "Canyon";
select count(distinct(gameid)) from oracle_elixir where patch = 14.13;
select * from champion_score_jungle where patch = "14.15" and name_us = "Olaf";
select name_us, playername from oracle_elixir where position = "jungle" and playername !="Sylvie"  and gameid in (select gameid from oracle_elixir where playername = "Sylvie" and name_us = "Maokai");
select * from champion_score_jungle where  patch = 14.15 order by (pick_rate);


select count(distinct(name_us)) from champion_score_all;