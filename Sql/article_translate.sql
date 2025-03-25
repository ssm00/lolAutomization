create table article_translate(
	sequence bigint auto_increment primary key,
    original_title text, 
    original_content text,
    main_title text,
    sub_title text,
    content text,
    prompt_version int,
    model varchar(50),
    original_seq bigint,
	FOREIGN KEY (original_seq) REFERENCES article(sequence)
);

select * from article_translate;
