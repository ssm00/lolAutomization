create table tournament_info(
	seq int auto_increment primary key,
    official_site_id varchar(100),
    official_site_slug varchar(100) unique,
    league_seq int,
    start_date date,
    foreign key (league_seq) references league_info(seq)
);
select * from tournament_info;