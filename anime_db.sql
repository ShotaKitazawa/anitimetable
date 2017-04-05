create table anime(
	anime_id int AUTO_INCREMENT, name varchar(64), 
	PRIMARY KEY(anime_id)
);
create table anime_brand(
	anime_id int, brand_id int,
	PRIMARY KEY(anime_id, brand_id)
);
create table brand(
	brand_id int AUTO_INCREMENT, name varchar(32),
	PRIMARY KEY(brand_id)
);
create table anime_writer(
	anime_id int, writer_id int,
	PRIMARY KEY(anime_id, writer_id)
);
create table writer(
	writer_id int AUTO_INCREMENT, name varchar(32),
	PRIMARY KEY(writer_id)
);
create table anime_director(
	anime_id int, director_id int,
	PRIMARY KEY(anime_id, director_id)
);
create table director(
	director_id int AUTO_INCREMENT, name varchar(32),
	PRIMARY KEY(director_id)
);
create table anime_op(
	anime_id int, op_id int,
	PRIMARY KEY(anime_id, op_id)
);
create table op(
	op_id int AUTO_INCREMENT, name varchar(64), singer_id int,
	PRIMARY KEY(op_id, singer_id)
);
create table anime_ed(
	anime_id int, ed_id int,
	PRIMARY KEY(anime_id, ed_id)
);
create table ed(
	ed_id int AUTO_INCREMENT, name varchar(64), singer_id int,
	PRIMARY KEY(ed_id, singer_id)
);
create table singer(
	singer_id int AUTO_INCREMENT, name varchar(512), 
	PRIMARY KEY(singer_id)
);
create table anime_actor(
	anime_id int, actor_id int,
	PRIMARY KEY(anime_id, actor_id)
);
create table actor(
	actor_id int AUTO_INCREMENT, name varchar(32), 
	PRIMARY KEY(actor_id)
); 
create table anime_broadcaster(
	anime_id int, broadcaster_id int, weekday varchar(4), time varchar(16), 
	PRIMARY KEY(anime_id, broadcaster_id)
);
create table broadcaster(
	broadcaster_id int, name varchar(32), 
	PRIMARY KEY(broadcaster_id)
);
create table users(
	uid int(10) AUTO_INCREMENT, user_name varchar(10), pass_hash varchar(20), 
	PRIMARY KEY(uid)
);
create table userreview(
	uid int(10), anime_id int, tokuten int, 
	tourokubi int, hitokoto varchar(200), 
	PRIMARY KEY(anime_id, uid)
);
create table userhighlight(
	uid int(10), anime_id int, broadcaster_id int, 
	PRIMARY KEY(uid, anime_id, broadcaster_id)
);

insert into broadcaster values (02, "NHK Eテレ");
insert into broadcaster values (04, "日本テレビ");
insert into broadcaster values (05, "テレビ朝日");
insert into broadcaster values (06, "TBS");
insert into broadcaster values (07, "テレビ東京");
insert into broadcaster values (08, "フジテレビ");
insert into broadcaster values (09, "TOKYO MX");
insert into broadcaster values (10, "AT-X");
