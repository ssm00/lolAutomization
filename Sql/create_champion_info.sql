create table champion_info (
	seq int primary key auto_increment,
    ps_name varchar(50),
    lol_official_image_name varchar(50),
    name_kr varchar(50)
);

select * from champion_info;
update champion_info set lol_official_image_name = "DrMundo" where lol_official_image_name = "Dr.Mundo";
update champion_info set lol_official_image_name = "KSante" where lol_official_image_name = "Ksante";
update champion_info set lol_official_image_name = "KogMaw" where lol_official_image_name = "Kogmaw";
update champion_info set lol_official_image_name = "Leblanc" where lol_official_image_name = "LeBlanc";
update champion_info set lol_official_image_name = "Nunu" where lol_official_image_name = "Nunu&Willump";
update champion_info set lol_official_image_name = "Renata" where lol_official_image_name = "RenataGlasc";
update champion_info set lol_official_image_name = "MonkeyKing" where lol_official_image_name = "Wukong";


