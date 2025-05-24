-- Η ιδέα της χρήσης της σχεσιακής βάσης δεδομένων με τους ναυτικούς ποι νοικιάζουν σκάφη και τα παραλαμβάνουν από 
-- μαρίνες ανήκει στους R. Ramakrishnan και J. Gehrke συγγραφείς του βιβλίου "Συστήματα Διαχείρισης Βάσεων ΔΕδομένων", 
-- εκδόσεις Α. Τζιόλα και Υιοί Α.Ε, ISBN: 978-960-418-8

-- Ο κώδικας SQL που ακολουθεί εκτελείται απρόσκοπτα στο περιβάλλον PostgreSQL RDBMS

-- Καταργούνται/διαγράφονται οι πίνακες sailors.reservation, sailors.marina, sailors.boat, sailors.sailor που, ενδεχομένως, υπάρχουν ήδη.
drop table if exists sailors.reservation;
drop table if exists sailors.marina;
drop table if exists sailors.boat;
drop table if exists sailors.sailor;

-- Δημιουργία του πίνακα sailors.boat
create table sailors.boat
    (bid integer not null constraint c_bid primary key,
     bname varchar(40),
     color varchar(40) 
     constraint c_color check (color in ('Red','Blue','Light Green','Yellow')));

-- Δημιουργία του πίνακα sailors.marina
create table sailors.marina
    (mid integer not null constraint m_key primary key,
     name varchar(40) not null,
    capacity integer);

-- Δημιουργία του πίνακα sailors.sailor
create table sailors.sailor 
    (sid integer not null constraint c_sid primary key,
     sname varchar(40),
     rating integer constraint c_rating check (rating between 1 and 10),
     age real constraint  c_age check (age <= 18));

-- Δημιουργία του πίνακα sailors.reservation.
create table sailors.reservation
    (sid integer not null constraint f_key1 references sailors.sailor(sid) on delete cascade on update cascade,
    bid integer not null constraint f_key2 references sailors.boat(bid) on delete restrict on update restrict
                                   constraint c_bid check (bid not in (999)),
    mid integer constraint f_key3 references sailors.marina(mid) on delete set null on update set null, 
    r_date date not null constraint c_date check (r_date > '02/04/1998'), 
    constraint p_key primary key(sid,bid,r_date));
