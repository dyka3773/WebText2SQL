DROP TABLE IF EXISTS customer_customer_demo;
DROP TABLE IF EXISTS customer_demographics;
DROP TABLE IF EXISTS employee_territories;
DROP TABLE IF EXISTS order_details;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS shippers;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS territories;
DROP TABLE IF EXISTS us_states;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS region;
DROP TABLE IF EXISTS employees;

CREATE TABLE northwind.categories (
    category_id smallint NOT NULL PRIMARY KEY,
    category_name character varying(15) NOT NULL,
    description text,
    picture bytea
);

CREATE TABLE northwind.customer_demographics (
    customer_type_id bpchar NOT NULL PRIMARY KEY,
    customer_desc text
);

CREATE TABLE northwind.customers (
    customer_id bpchar NOT NULL PRIMARY KEY,
    company_name character varying(40) NOT NULL,
    contact_name character varying(30),
    contact_title character varying(30),
    address character varying(60),
    city character varying(15),
    region character varying(15),
    postal_code character varying(10),
    country character varying(15),
    phone character varying(24),
    fax character varying(24)
);

CREATE TABLE northwind.customer_customer_demo (
    customer_id bpchar NOT NULL,
    customer_type_id bpchar NOT NULL,
    PRIMARY KEY (customer_id, customer_type_id),
    FOREIGN KEY (customer_type_id) REFERENCES northwind.customer_demographics,
    FOREIGN KEY (customer_id) REFERENCES northwind.customers
);

CREATE TABLE northwind.employees (
    employee_id smallint NOT NULL PRIMARY KEY,
    last_name character varying(20) NOT NULL,
    first_name character varying(10) NOT NULL,
    title character varying(30),
    title_of_courtesy character varying(25),
    birth_date date,
    hire_date date,
    address character varying(60),
    city character varying(15),
    region character varying(15),
    postal_code character varying(10),
    country character varying(15),
    home_phone character varying(24),
    extension character varying(4),
    photo bytea,
    notes text,
    reports_to smallint,
    photo_path character varying(255),
	FOREIGN KEY (reports_to) REFERENCES northwind.employees
);

CREATE TABLE northwind.suppliers (
    supplier_id smallint NOT NULL PRIMARY KEY,
    company_name character varying(40) NOT NULL,
    contact_name character varying(30),
    contact_title character varying(30),
    address character varying(60),
    city character varying(15),
    region character varying(15),
    postal_code character varying(10),
    country character varying(15),
    phone character varying(24),
    fax character varying(24),
    homepage text
);

CREATE TABLE northwind.products (
    product_id smallint NOT NULL PRIMARY KEY,
    product_name character varying(40) NOT NULL,
    supplier_id smallint,
    category_id smallint,
    quantity_per_unit character varying(20),
    unit_price real,
    units_in_stock smallint,
    units_on_order smallint,
    reorder_level smallint,
    discontinued integer NOT NULL,
	FOREIGN KEY (category_id) REFERENCES northwind.categories,
	FOREIGN KEY (supplier_id) REFERENCES northwind.suppliers
);

CREATE TABLE northwind.region (
    region_id smallint NOT NULL PRIMARY KEY,
    region_description bpchar NOT NULL
);

CREATE TABLE northwind.shippers (
    shipper_id smallint NOT NULL PRIMARY KEY,
    company_name character varying(40) NOT NULL,
    phone character varying(24)
);

CREATE TABLE northwind.orders (
    order_id smallint NOT NULL PRIMARY KEY,
    customer_id bpchar,
    employee_id smallint,
    order_date date,
    required_date date,
    shipped_date date,
    ship_via smallint,
    freight real,
    ship_name character varying(40),
    ship_address character varying(60),
    ship_city character varying(15),
    ship_region character varying(15),
    ship_postal_code character varying(10),
    ship_country character varying(15),
    FOREIGN KEY (customer_id) REFERENCES northwind.customers,
    FOREIGN KEY (employee_id) REFERENCES northwind.employees,
    FOREIGN KEY (ship_via) REFERENCES northwind.shippers
);

CREATE TABLE northwind.territories (
    territory_id character varying(20) NOT NULL PRIMARY KEY,
    territory_description bpchar NOT NULL,
    region_id smallint NOT NULL,
	FOREIGN KEY (region_id) REFERENCES northwind.region
);

CREATE TABLE northwind.employee_territories (
    employee_id smallint NOT NULL,
    territory_id character varying(20) NOT NULL,
    PRIMARY KEY (employee_id, territory_id),
    FOREIGN KEY (territory_id) REFERENCES northwind.territories,
    FOREIGN KEY (employee_id) REFERENCES northwind.employees
);

CREATE TABLE northwind.order_details (
    order_id smallint NOT NULL,
    product_id smallint NOT NULL,
    unit_price real NOT NULL,
    quantity smallint NOT NULL,
    discount real NOT NULL,
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (product_id) REFERENCES northwind.products,
    FOREIGN KEY (order_id) REFERENCES northwind.orders
);

CREATE TABLE northwind.us_states (
    state_id smallint NOT NULL PRIMARY KEY,
    state_name character varying(100),
    state_abbr character varying(2),
    state_region character varying(50)
);
