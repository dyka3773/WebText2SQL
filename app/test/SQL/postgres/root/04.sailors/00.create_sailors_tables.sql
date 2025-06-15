drop table if exists sailors.reservation;
drop table if exists sailors.marina;
drop table if exists sailors.boat;
drop table if exists sailors.sailor;

create table sailors.boat
    (bid integer not null constraint c_bid primary key,
     bname varchar(40),
     color varchar(40) 
     constraint c_color check (color in ('Red','Blue','Light Green','Yellow')));

create table sailors.marina
    (mid integer not null constraint m_key primary key,
     name varchar(40) not null,
    capacity integer);

create table sailors.sailor 
    (sid integer not null constraint c_sid primary key,
     sname varchar(40),
     rating integer constraint c_rating check (rating between 1 and 10),
     age real constraint  c_age check (age <= 18));

create table sailors.reservation
    (sid integer not null constraint f_key1 references sailors.sailor(sid) on delete cascade on update cascade,
    bid integer not null constraint f_key2 references sailors.boat(bid) on delete restrict on update restrict
                                   constraint c_bid check (bid not in (999)),
    mid integer constraint f_key3 references sailors.marina(mid) on delete set null on update set null, 
    r_date date not null constraint c_date check (r_date > '02/04/1998'), 
    constraint p_key primary key(sid,bid,r_date));
