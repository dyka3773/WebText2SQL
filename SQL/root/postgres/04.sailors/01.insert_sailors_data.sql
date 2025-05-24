-- Εισαγωγή δεδομένων (γραμμών) στον πίνακα sailors.sailor
INSERT INTO sailors.sailor(sid,sname,rating,age) VALUES (2, 'Γιάννης', 6, 17);
INSERT INTO sailors.sailor(sid,sname,rating,age) VALUES (11, 'Μαρία', 10, 18);
INSERT INTO sailors.sailor(sid,sname,rating,age) VALUES (12, 'Θανάσης', 7, 14);
INSERT INTO sailors.sailor(sid,sname,rating,age) VALUES (13, 'Γιάννης', 9, 18);
INSERT INTO sailors.sailor(sid,sname,rating,age) VALUES (1, 'Χριστίνα', 10, 17);
INSERT INTO sailors.sailor(sid,sname,rating,age) VALUES (15, 'Θόδωρος', 10, 13);
INSERT INTO sailors.sailor(sid,sname,rating,age) VALUES (16, 'Λεωνίδας', 5, 13);
INSERT INTO sailors.sailor(sid,sname,age) VALUES (17,'Ελευθερία',17);
INSERT INTO sailors.sailor(sid,sname,rating,age) VALUES (19,'Πολύκαρπος',1,16);
INSERT INTO sailors.sailor(sid,sname,rating,age) VALUES (27,'Μαριάνθη',8,15);
INSERT INTO sailors.sailor(sid,sname,rating,age) VALUES (37,'Κώστας',8,14);


-- Εισαγωγή δεδομένων (γραμμών) στον πίνακα sailors.marina
INSERT INTO sailors.marina(mid,name,capacity) VALUES(33,'Πόρτο Καρράς',300);
INSERT INTO sailors.marina(mid,name,capacity) VALUES(5,'Καλαμαριά',105);
INSERT INTO sailors.marina(mid,name,capacity) VALUES(1,'Πλαταμώνας',32);
INSERT INTO sailors.marina(mid,name,capacity) VALUES(7,'Ποσείδι',19);
INSERT INTO sailors.marina(mid,name,capacity) VALUES(2,'Ουρανούπολις',105);

-- Εισαγωγή δεδομένων (γραμμών) στον πίνακα sailors.boat
INSERT INTO sailors.boat(bid,bname,color) VALUES(88,'Σοφία','Blue');
INSERT INTO sailors.boat(bid,bname,color) VALUES(17,'Αγ. Αικατερίνη','Light Green');
INSERT INTO sailors.boat(bid,bname,color) VALUES(13,'Παναγής','Yellow');
INSERT INTO sailors.boat(bid,bname,color) VALUES(1,'Αγ. Νικόλαος','Red');
INSERT INTO sailors.boat(bid,bname,color) VALUES(72,'Χριστινάκι','Red');
INSERT INTO sailors.boat(bid,bname,color) VALUES(19,'Δήλος','Light Green');
INSERT INTO sailors.boat(bid,bname,color) VALUES(77,'Αγ. Γεώργιος','Blue');

-- Εισαγωγή δεδομένων (γραμμών) στον πίνακα sailors.reservation
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(2,88,7,'1999-02-17');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(12,17,2,'1998-05-17');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(11,17,2,'1999-01-17');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(13,13,7,'2003-01-13');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(11,13,33,'2000-05-05');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(1,1,33,'2000-05-05');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(1,13,33,'2000-05-06');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(1,17,33,'2000-05-07');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(1,19,33,'2000-05-08');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(1,72,33,'2000-05-09');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(1,88,33,'2000-05-10');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(1,77,2,'2000-08-10');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(19,13,33,'1999-10-12');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(27,88,7,'2000-06-11');
INSERT INTO sailors.reservation(sid,bid,mid,r_date) VALUES(37,72,2,'2001-04-27');
