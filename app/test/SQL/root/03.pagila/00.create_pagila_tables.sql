SET search_path TO pagila;

CREATE SEQUENCE actor_actor_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE actor (
    actor_id integer DEFAULT nextval('actor_actor_id_seq'::regclass) NOT NULL,
    first_name character varying(45) NOT NULL,
    last_name character varying(45) NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);

CREATE TYPE mpaa_rating AS ENUM (
    'G',
    'PG',
    'PG-13',
    'R',
    'NC-17'
);

CREATE DOMAIN year AS integer CONSTRAINT year_check CHECK (((VALUE >= 1901) AND (VALUE <= 2155)));

CREATE FUNCTION _group_concat(text, text) RETURNS text
    AS $_$
SELECT CASE
  WHEN $2 IS NULL THEN $1
  WHEN $1 IS NULL THEN $2
  ELSE $1 || ', ' || $2
END
$_$
    LANGUAGE sql IMMUTABLE;

CREATE AGGREGATE group_concat(text) (
    SFUNC = _group_concat,
    STYPE = text
);

CREATE SEQUENCE category_category_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE category (
    category_id integer DEFAULT nextval('category_category_id_seq'::regclass) NOT NULL,
    name character varying(25) NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE film_film_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE film (
    film_id integer DEFAULT nextval('film_film_id_seq'::regclass) NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    release_year year,
    language_id smallint NOT NULL,
    original_language_id smallint,
    rental_duration smallint DEFAULT 3 NOT NULL,
    rental_rate numeric(4,2) DEFAULT 4.99 NOT NULL,
    length smallint,
    replacement_cost numeric(5,2) DEFAULT 19.99 NOT NULL,
    rating mpaa_rating DEFAULT 'G'::mpaa_rating,
    last_update timestamp without time zone DEFAULT now() NOT NULL,
    special_features text[],
    fulltext tsvector NOT NULL
);

CREATE TABLE film_actor (
    actor_id smallint NOT NULL,
    film_id smallint NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);

CREATE TABLE film_category (
    film_id smallint NOT NULL,
    category_id smallint NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);

CREATE VIEW actor_info AS
    SELECT a.actor_id, a.first_name, a.last_name, group_concat(DISTINCT (((c.name)::text || ': '::text) || (SELECT group_concat((f.title)::text) AS group_concat FROM ((film f JOIN film_category fc ON ((f.film_id = fc.film_id))) JOIN film_actor fa ON ((f.film_id = fa.film_id))) WHERE ((fc.category_id = c.category_id) AND (fa.actor_id = a.actor_id)) GROUP BY fa.actor_id))) AS film_info FROM (((actor a LEFT JOIN film_actor fa ON ((a.actor_id = fa.actor_id))) LEFT JOIN film_category fc ON ((fa.film_id = fc.film_id))) LEFT JOIN category c ON ((fc.category_id = c.category_id))) GROUP BY a.actor_id, a.first_name, a.last_name;

CREATE SEQUENCE address_address_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE address (
    address_id integer DEFAULT nextval('address_address_id_seq'::regclass) NOT NULL,
    address character varying(50) NOT NULL,
    address2 character varying(50),
    district character varying(20) NOT NULL,
    city_id smallint NOT NULL,
    postal_code character varying(10),
    phone character varying(20) NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE city_city_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE city (
    city_id integer DEFAULT nextval('city_city_id_seq'::regclass) NOT NULL,
    city character varying(50) NOT NULL,
    country_id smallint NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE country_country_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE country (
    country_id integer DEFAULT nextval('country_country_id_seq'::regclass) NOT NULL,
    country character varying(50) NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE customer_customer_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE customer (
    customer_id integer DEFAULT nextval('customer_customer_id_seq'::regclass) NOT NULL,
    store_id smallint NOT NULL,
    first_name character varying(45) NOT NULL,
    last_name character varying(45) NOT NULL,
    email character varying(50),
    address_id smallint NOT NULL,
    activebool boolean DEFAULT true NOT NULL,
    create_date date DEFAULT ('now'::text)::date NOT NULL,
    last_update timestamp without time zone DEFAULT now(),
    active integer
);

CREATE VIEW customer_list AS
    SELECT cu.customer_id AS id, (((cu.first_name)::text || ' '::text) || (cu.last_name)::text) AS name, a.address, a.postal_code AS "zip code", a.phone, city.city, country.country, CASE WHEN cu.activebool THEN 'active'::text ELSE ''::text END AS notes, cu.store_id AS sid FROM (((customer cu JOIN address a ON ((cu.address_id = a.address_id))) JOIN city ON ((a.city_id = city.city_id))) JOIN country ON ((city.country_id = country.country_id)));

CREATE VIEW film_list AS
    SELECT film.film_id AS fid, film.title, film.description, category.name AS category, film.rental_rate AS price, film.length, film.rating, group_concat((((actor.first_name)::text || ' '::text) || (actor.last_name)::text)) AS actors FROM ((((category LEFT JOIN film_category ON ((category.category_id = film_category.category_id))) LEFT JOIN film ON ((film_category.film_id = film.film_id))) JOIN film_actor ON ((film.film_id = film_actor.film_id))) JOIN actor ON ((film_actor.actor_id = actor.actor_id))) GROUP BY film.film_id, film.title, film.description, category.name, film.rental_rate, film.length, film.rating;

CREATE SEQUENCE inventory_inventory_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE inventory (
    inventory_id integer DEFAULT nextval('inventory_inventory_id_seq'::regclass) NOT NULL,
    film_id smallint NOT NULL,
    store_id smallint NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE language_language_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE language (
    language_id integer DEFAULT nextval('language_language_id_seq'::regclass) NOT NULL,
    name character(20) NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);

CREATE VIEW nicer_but_slower_film_list AS
    SELECT film.film_id AS fid, film.title, film.description, category.name AS category, film.rental_rate AS price, film.length, film.rating, group_concat((((upper("substring"((actor.first_name)::text, 1, 1)) || lower("substring"((actor.first_name)::text, 2))) || upper("substring"((actor.last_name)::text, 1, 1))) || lower("substring"((actor.last_name)::text, 2)))) AS actors FROM ((((category LEFT JOIN film_category ON ((category.category_id = film_category.category_id))) LEFT JOIN film ON ((film_category.film_id = film.film_id))) JOIN film_actor ON ((film.film_id = film_actor.film_id))) JOIN actor ON ((film_actor.actor_id = actor.actor_id))) GROUP BY film.film_id, film.title, film.description, category.name, film.rental_rate, film.length, film.rating;

CREATE SEQUENCE payment_payment_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE payment (
    payment_id integer DEFAULT nextval('payment_payment_id_seq'::regclass) NOT NULL,
    customer_id smallint NOT NULL,
    staff_id smallint NOT NULL,
    rental_id integer NOT NULL,
    amount numeric(5,2) NOT NULL,
    payment_date timestamp without time zone NOT NULL
);
CREATE SEQUENCE rental_rental_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE rental (
    rental_id integer DEFAULT nextval('rental_rental_id_seq'::regclass) NOT NULL,
    rental_date timestamp without time zone NOT NULL,
    inventory_id integer NOT NULL,
    customer_id smallint NOT NULL,
    return_date timestamp without time zone,
    staff_id smallint NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);

CREATE VIEW sales_by_film_category AS
    SELECT c.name AS category, sum(p.amount) AS total_sales FROM (((((payment p JOIN rental r ON ((p.rental_id = r.rental_id))) JOIN inventory i ON ((r.inventory_id = i.inventory_id))) JOIN film f ON ((i.film_id = f.film_id))) JOIN film_category fc ON ((f.film_id = fc.film_id))) JOIN category c ON ((fc.category_id = c.category_id))) GROUP BY c.name ORDER BY sum(p.amount) DESC;

CREATE SEQUENCE staff_staff_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE staff (
    staff_id integer DEFAULT nextval('staff_staff_id_seq'::regclass) NOT NULL,
    first_name character varying(45) NOT NULL,
    last_name character varying(45) NOT NULL,
    address_id smallint NOT NULL,
    email character varying(50),
    store_id smallint NOT NULL,
    active boolean DEFAULT true NOT NULL,
    username character varying(16) NOT NULL,
    password character varying(40),
    last_update timestamp without time zone DEFAULT now() NOT NULL,
    picture bytea
);

CREATE SEQUENCE store_store_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

CREATE TABLE store (
    store_id integer DEFAULT nextval('store_store_id_seq'::regclass) NOT NULL,
    manager_staff_id smallint NOT NULL,
    address_id smallint NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);

CREATE VIEW sales_by_store AS
    SELECT (((c.city)::text || ','::text) || (cy.country)::text) AS store, (((m.first_name)::text || ' '::text) || (m.last_name)::text) AS manager, sum(p.amount) AS total_sales FROM (((((((payment p JOIN rental r ON ((p.rental_id = r.rental_id))) JOIN inventory i ON ((r.inventory_id = i.inventory_id))) JOIN store s ON ((i.store_id = s.store_id))) JOIN address a ON ((s.address_id = a.address_id))) JOIN city c ON ((a.city_id = c.city_id))) JOIN country cy ON ((c.country_id = cy.country_id))) JOIN staff m ON ((s.manager_staff_id = m.staff_id))) GROUP BY cy.country, c.city, s.store_id, m.first_name, m.last_name ORDER BY cy.country, c.city;

CREATE VIEW staff_list AS
    SELECT s.staff_id AS id, (((s.first_name)::text || ' '::text) || (s.last_name)::text) AS name, a.address, a.postal_code AS "zip code", a.phone, city.city, country.country, s.store_id AS sid FROM (((staff s JOIN address a ON ((s.address_id = a.address_id))) JOIN city ON ((a.city_id = city.city_id))) JOIN country ON ((city.country_id = country.country_id)));

CREATE FUNCTION inventory_in_stock(p_inventory_id integer) RETURNS boolean
    AS $$
DECLARE
    v_rentals INTEGER;
    v_out     INTEGER;
BEGI
    SELECT count(*) INTO v_rentals
    FROM rental
    WHERE inventory_id = p_inventory_id;

    IF v_rentals = 0 THEN
      RETURN TRUE;
    END IF;

    SELECT COUNT(rental_id) INTO v_out
    FROM inventory LEFT JOIN rental USING(inventory_id)
    WHERE inventory.inventory_id = p_inventory_id
    AND rental.return_date IS NULL;

    IF v_out > 0 THEN
      RETURN FALSE;
    ELSE
      RETURN TRUE;
    END IF;
END $$
    LANGUAGE plpgsql;

CREATE FUNCTION film_in_stock(p_film_id integer, p_store_id integer, OUT p_film_count integer) RETURNS SETOF integer
    AS $_$
     SELECT inventory_id
     FROM inventory
     WHERE film_id = $1
     AND store_id = $2
     AND inventory_in_stock(inventory_id);
$_$
    LANGUAGE sql;

CREATE FUNCTION film_not_in_stock(p_film_id integer, p_store_id integer, OUT p_film_count integer) RETURNS SETOF integer
    AS $_$
    SELECT inventory_id
    FROM inventory
    WHERE film_id = $1
    AND store_id = $2
    AND NOT inventory_in_stock(inventory_id);
$_$
    LANGUAGE sql;

CREATE FUNCTION get_customer_balance(p_customer_id integer, p_effective_date timestamp without time zone) RETURNS numeric
    AS $$DECLARE
    v_rentfees DECIMAL(5,2    v_overfees INTEGER;       v_payments DECIMAL(5,2BEGIN
    SELECT COALESCE(SUM(film.rental_rate),0) INTO v_rentfees
    FROM film, inventory, rental
    WHERE film.film_id = inventory.film_id
      AND inventory.inventory_id = rental.inventory_id
      AND rental.rental_date <= p_effective_date
      AND rental.customer_id = p_customer_id;

    SELECT COALESCE(SUM(IF((rental.return_date - rental.rental_date) > (film.rental_duration * '1 day'::interval),
        ((rental.return_date - rental.rental_date) - (film.rental_duration * '1 day'::interval)),0)),0) INTO v_overfees
    FROM rental, inventory, film
    WHERE film.film_id = inventory.film_id
      AND inventory.inventory_id = rental.inventory_id
      AND rental.rental_date <= p_effective_date
      AND rental.customer_id = p_customer_id;

    SELECT COALESCE(SUM(payment.amount),0) INTO v_payments
    FROM payment
    WHERE payment.payment_date <= p_effective_date
    AND payment.customer_id = p_customer_id;

    RETURN v_rentfees + v_overfees - v_payments;
END
$$
    LANGUAGE plpgsql;

CREATE FUNCTION inventory_held_by_customer(p_inventory_id integer) RETURNS integer
    AS $$
DECLARE
    v_customer_id INTEGER;
BEGIN

  SELECT customer_id INTO v_customer_id
  FROM rental
  WHERE return_date IS NULL
  AND inventory_id = p_inventory_id;

  RETURN v_customer_id;
END $$
    LANGUAGE plpgsql;


CREATE FUNCTION last_day(timestamp without time zone) RETURNS date
    AS $_$
  SELECT CASE
    WHEN EXTRACT(MONTH FROM $1) = 12 THEN
      (((EXTRACT(YEAR FROM $1) + 1) operator(pg_catalog.||) '-01-01')::date - INTERVAL '1 day')::date
    ELSE
      ((EXTRACT(YEAR FROM $1) operator(pg_catalog.||) '-' operator(pg_catalog.||) (EXTRACT(MONTH FROM $1) + 1) operator(pg_catalog.||) '-01')::date - INTERVAL '1 day')::date
    END
$_$
    LANGUAGE sql IMMUTABLE STRICT;

CREATE FUNCTION last_updated() RETURNS trigger
    AS $$
BEGIN
    NEW.last_update = CURRENT_TIMESTAMP;
    RETURN NEW;
END $$
    LANGUAGE plpgsql;
CREATE FUNCTION rewards_report(min_monthly_purchases integer, min_dollar_amount_purchased numeric) RETURNS SETOF customer
    AS $_$
DECLARE
    last_month_start DATE;
    last_month_end DATE;
rr RECORD;
tmpSQL TEXT;
BEGIN

    /* Some sanity checks... */
    IF min_monthly_purchases = 0 THEN
        RAISE EXCEPTION 'Minimum monthly purchases parameter must be > 0';
    END IF;
    IF min_dollar_amount_purchased = 0.00 THEN
        RAISE EXCEPTION 'Minimum monthly dollar amount purchased parameter must be > $0.00';
    END IF;

    last_month_start := CURRENT_DATE - '3 month'::interval;
    last_month_start := to_date((extract(YEAR FROM last_month_start) || '-' || extract(MONTH FROM last_month_start) || '-01'),'YYYY-MM-DD');
    last_month_end := LAST_DAY(last_month_start);

    /*
    Create a temporary storage area for Customer IDs.
    */
    CREATE TEMPORARY TABLE tmpCustomer (customer_id INTEGER NOT NULL PRIMARY KEY);

    /*
    Find all customers meeting the monthly purchase requirements
    */

    tmpSQL := 'INSERT INTO tmpCustomer (customer_id)
        SELECT p.customer_id
        FROM payment AS p
        WHERE DATE(p.payment_date) BETWEEN '||quote_literal(last_month_start) ||' AND '|| quote_literal(last_month_end) || '
        GROUP BY customer_id
        HAVING SUM(p.amount) > '|| min_dollar_amount_purchased || '
        AND COUNT(customer_id) > ' ||min_monthly_purchases ;

    EXECUTE tmpSQL;

    /*
    Output ALL customer information of matching rewardees.
    Customize output as needed.
    */
    FOR rr IN EXECUTE 'SELECT c.* FROM tmpCustomer AS t INNER JOIN customer AS c ON t.customer_id = c.customer_id' LOOP
        RETURN NEXT rr;
    END LOOP;

    /* Clean up */
    tmpSQL := 'DROP TABLE tmpCustomer';
    EXECUTE tmpSQL;

RETURN;
END
$_$
    LANGUAGE plpgsql SECURITY DEFINER;

ALTER TABLE ONLY actor
    ADD CONSTRAINT actor_pkey PRIMARY KEY (actor_id);
ALTER TABLE ONLY address
    ADD CONSTRAINT address_pkey PRIMARY KEY (address_id);
ALTER TABLE ONLY category
    ADD CONSTRAINT category_pkey PRIMARY KEY (category_id);
ALTER TABLE ONLY city
    ADD CONSTRAINT city_pkey PRIMARY KEY (city_id);
ALTER TABLE ONLY country
    ADD CONSTRAINT country_pkey PRIMARY KEY (country_id);
ALTER TABLE ONLY customer
    ADD CONSTRAINT customer_pkey PRIMARY KEY (customer_id);
ALTER TABLE ONLY film_actor
    ADD CONSTRAINT film_actor_pkey PRIMARY KEY (actor_id, film_id);
ALTER TABLE ONLY film_category
    ADD CONSTRAINT film_category_pkey PRIMARY KEY (film_id, category_id);
ALTER TABLE ONLY film
    ADD CONSTRAINT film_pkey PRIMARY KEY (film_id);
ALTER TABLE ONLY inventory
    ADD CONSTRAINT inventory_pkey PRIMARY KEY (inventory_id);
ALTER TABLE ONLY language
    ADD CONSTRAINT language_pkey PRIMARY KEY (language_id);
ALTER TABLE ONLY payment
    ADD CONSTRAINT payment_pkey PRIMARY KEY (payment_id);
ALTER TABLE ONLY rental
    ADD CONSTRAINT rental_pkey PRIMARY KEY (rental_id);
ALTER TABLE ONLY staff
    ADD CONSTRAINT staff_pkey PRIMARY KEY (staff_id);
ALTER TABLE ONLY store
    ADD CONSTRAINT store_pkey PRIMARY KEY (store_id);

CREATE INDEX film_fulltext_idx ON film USING gist (fulltext);
CREATE INDEX idx_actor_last_name ON actor USING btree (last_name);
CREATE INDEX idx_fk_address_id ON customer USING btree (address_id);
CREATE INDEX idx_fk_city_id ON address USING btree (city_id);
CREATE INDEX idx_fk_country_id ON city USING btree (country_id);
CREATE INDEX idx_fk_customer_id ON payment USING btree (customer_id);
CREATE INDEX idx_fk_film_id ON film_actor USING btree (film_id);
CREATE INDEX idx_fk_inventory_id ON rental USING btree (inventory_id);
CREATE INDEX idx_fk_language_id ON film USING btree (language_id);
CREATE INDEX idx_fk_original_language_id ON film USING btree (original_language_id);
CREATE INDEX idx_fk_staff_id ON payment USING btree (staff_id);
CREATE INDEX idx_fk_store_id ON customer USING btree (store_id);
CREATE INDEX idx_last_name ON customer USING btree (last_name);
CREATE INDEX idx_store_id_film_id ON inventory USING btree (store_id, film_id);
CREATE INDEX idx_title ON film USING btree (title);
CREATE UNIQUE INDEX idx_unq_manager_staff_id ON store USING btree (manager_staff_id);
CREATE UNIQUE INDEX idx_unq_rental_rental_date_inventory_id_customer_id ON rental USING btree (rental_date, inventory_id, customer_id);

CREATE TRIGGER film_fulltext_trigger
    BEFORE INSERT OR UPDATE ON film
    FOR EACH ROW
    EXECUTE PROCEDURE tsvector_update_trigger('fulltext', 'pg_catalog.english', 'title', 'description');

CREATE TRIGGER last_updated
    BEFORE UPDATE ON actor
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON address
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON category
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON city
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON country
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON customer
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON film
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON film_actor
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON film_category
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON inventory
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON language
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON rental
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON staff
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

CREATE TRIGGER last_updated
    BEFORE UPDATE ON store
    FOR EACH ROW
    EXECUTE PROCEDURE last_updated();

ALTER TABLE ONLY address
    ADD CONSTRAINT address_city_id_fkey FOREIGN KEY (city_id) REFERENCES city(city_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY city
    ADD CONSTRAINT city_country_id_fkey FOREIGN KEY (country_id) REFERENCES country(country_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY customer
    ADD CONSTRAINT customer_address_id_fkey FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY customer
    ADD CONSTRAINT customer_store_id_fkey FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY film_actor
    ADD CONSTRAINT film_actor_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES actor(actor_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY film_actor
    ADD CONSTRAINT film_actor_film_id_fkey FOREIGN KEY (film_id) REFERENCES film(film_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY film_category
    ADD CONSTRAINT film_category_category_id_fkey FOREIGN KEY (category_id) REFERENCES category(category_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY film_category
    ADD CONSTRAINT film_category_film_id_fkey FOREIGN KEY (film_id) REFERENCES film(film_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY film
    ADD CONSTRAINT film_language_id_fkey FOREIGN KEY (language_id) REFERENCES language(language_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY film
    ADD CONSTRAINT film_original_language_id_fkey FOREIGN KEY (original_language_id) REFERENCES language(language_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY inventory
    ADD CONSTRAINT inventory_film_id_fkey FOREIGN KEY (film_id) REFERENCES film(film_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY inventory
    ADD CONSTRAINT inventory_store_id_fkey FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY payment
    ADD CONSTRAINT payment_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY payment
    ADD CONSTRAINT payment_rental_id_fkey FOREIGN KEY (rental_id) REFERENCES rental(rental_id) ON UPDATE CASCADE ON DELETE SET NULL;
ALTER TABLE ONLY payment
    ADD CONSTRAINT payment_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY rental
    ADD CONSTRAINT rental_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY rental
    ADD CONSTRAINT rental_inventory_id_fkey FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY rental
    ADD CONSTRAINT rental_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY staff
    ADD CONSTRAINT staff_address_id_fkey FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY staff
    ADD CONSTRAINT staff_store_id_fkey FOREIGN KEY (store_id) REFERENCES store(store_id);
ALTER TABLE ONLY store
    ADD CONSTRAINT store_address_id_fkey FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT;
ALTER TABLE ONLY store
    ADD CONSTRAINT store_manager_staff_id_fkey FOREIGN KEY (manager_staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT;
