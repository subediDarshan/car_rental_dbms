import streamlit as st
import oracledb
import hashlib
import datetime
import pandas as pd
import os
import time

# Database configuration
DB_USER = os.getenv("DB_USER", "car_rental_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password123")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "1521")
DB_SERVICE = os.getenv("DB_SERVICE", "XEPDB1")

def init_db():
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}") as conn:
            with conn.cursor() as cursor:
                # Create users table
                try:
                    cursor.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'USERS'")
                    (table_exists,) = cursor.fetchone()

                    if not table_exists:
                        cursor.execute('''
                            CREATE TABLE users (
                                user_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                username VARCHAR2(100) UNIQUE NOT NULL,
                                password VARCHAR2(255) NOT NULL,
                                user_type VARCHAR2(50) NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        ''')
                except oracledb.DatabaseError as e:
                    error, = e.args
                    if error.code != 955:  # Table already exists
                        raise
                
                # Create customer table
                try:
                    cursor.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'CUSTOMER'")
                    (table_exists,) = cursor.fetchone()

                    if not table_exists:
                        cursor.execute('''
                        CREATE TABLE customer (
                            customer_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            user_id NUMBER,
                            name VARCHAR2(100) NOT NULL,
                            email VARCHAR2(100),
                            phone VARCHAR2(50),
                            address VARCHAR2(200),
                            street VARCHAR2(100),
                            city VARCHAR2(100),
                            id_number VARCHAR2(20),
                            license VARCHAR2(20),
                            CONSTRAINT fk_customer_user_id FOREIGN KEY (user_id) REFERENCES users(user_id)
                        )
                        ''')
                except oracledb.DatabaseError as e:
                    error, = e.args
                    if error.code != 955:
                        raise
                
                # Create employee table
                try:
                    cursor.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'EMPLOYEE'")
                    (table_exists,) = cursor.fetchone()

                    if not table_exists:
                        cursor.execute('''
                        CREATE TABLE employee (
                            emp_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            user_id NUMBER,
                            name VARCHAR2(100) NOT NULL,
                            email VARCHAR2(100),
                            phone VARCHAR2(50),
                            address VARCHAR2(200),
                            street VARCHAR2(100),
                            city VARCHAR2(100),
                            CONSTRAINT fk_employee_user_id FOREIGN KEY (user_id) REFERENCES users(user_id)
                        )
                        ''')
                except oracledb.DatabaseError as e:
                    error, = e.args
                    if error.code != 955:
                        raise
                
                # Create car table
                try:
                    cursor.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'CAR'")
                    (table_exists,) = cursor.fetchone()

                    if not table_exists:
                        cursor.execute('''
                        CREATE TABLE car (
                            car_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            model VARCHAR2(100) NOT NULL,
                            plate_no VARCHAR2(20) UNIQUE NOT NULL,
                            daily_price NUMBER NOT NULL
                        )
                        ''')
                except oracledb.DatabaseError as e:
                    error, = e.args
                    if error.code != 955:
                        raise
                
                # Create reservation table
                try:
                    cursor.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'RESERVE'")
                    (table_exists,) = cursor.fetchone()

                    if not table_exists:
                        cursor.execute('''
                        CREATE TABLE reserve (
                            resv_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            customer_id NUMBER NOT NULL,
                            car_id NUMBER NOT NULL,
                            pickup_day DATE NOT NULL,
                            reserve_date DATE DEFAULT CURRENT_DATE,
                            status VARCHAR2(50) DEFAULT 'Pending',
                            CONSTRAINT fk_reserve_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
                            CONSTRAINT fk_reserve_car FOREIGN KEY (car_id) REFERENCES car(car_id)
                        )
                        ''')
                except oracledb.DatabaseError as e:
                    error, = e.args
                    if error.code != 955:
                        raise
                
                # Create payments table
                try:
                    cursor.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'PAYMENTS'")
                    (table_exists,) = cursor.fetchone()

                    if not table_exists:
                        cursor.execute('''
                        CREATE TABLE payments (
                            pay_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            customer_id NUMBER NOT NULL,
                            amount NUMBER NOT NULL,
                            pay_date DATE DEFAULT CURRENT_DATE,
                            due_date DATE,
                            method VARCHAR2(50),
                            pay_status VARCHAR2(50) DEFAULT 'Pending',
                            employee_id NUMBER,
                            CONSTRAINT fk_payments_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
                            CONSTRAINT fk_payments_employee FOREIGN KEY (employee_id) REFERENCES employee(emp_id)
                        )
                        ''')
                except oracledb.DatabaseError as e:
                    error, = e.args
                    if error.code != 955:
                        raise
                
                # Add trigger to check reservation date
                try:
                    cursor.execute("""
                    CREATE OR REPLACE TRIGGER check_reservation_date
                    BEFORE INSERT ON reserve
                    FOR EACH ROW
                    DECLARE
                        v_days NUMBER;
                    BEGIN
                        v_days := :NEW.pickup_day - CURRENT_DATE;
                        IF v_days < 0 THEN
                            RAISE_APPLICATION_ERROR(-20001, 'Pickup date cannot be before current date');
                        END IF;
                    END;
                    """)
                except oracledb.DatabaseError as e:
                    error, = e.args
                    if error.code != 4081:  # Trigger already exists
                        raise
                
                # Insert sample cars if none exist
                cursor.execute("SELECT COUNT(*) FROM car")
                car_count, = cursor.fetchone()
                
                if car_count == 0:
                    sample_cars = [
                        ('Toyota Camry', 'ABC123', 50),
                        ('Honda Accord', 'XYZ789', 55),
                        ('Tesla Model 3', 'EV1234', 85),
                        ('Ford Mustang', 'MST500', 75),
                        ('Jeep Cherokee', 'JEP321', 65)
                    ]
                    
                    cursor.executemany(
                        "INSERT INTO car (model, plate_no, daily_price) VALUES (:1, :2, :3)",
                        sample_cars
                    )
                
                # Insert admin user if none exists
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
                admin_count, = cursor.fetchone()
                
                if admin_count == 0:
                    admin_password = hash_password('admin123')
                    cursor.execute(
                        "INSERT INTO users (username, password, user_type) VALUES ('admin', :1, 'Employee')",
                        [admin_password]
                    )
                    
                    # Get the user_id for the admin
                    cursor.execute("SELECT user_id FROM users WHERE username = 'admin'")
                    admin_user_id, = cursor.fetchone()
                    
                    # Create an employee record for the admin
                    cursor.execute(
                        "INSERT INTO employee (user_id, name, email, phone, address) VALUES (:1, 'Admin User', 'admin@carental.com', '555-ADMIN', 'Main Office')",
                        [admin_user_id]
                    )
                
                conn.commit()
                
    except oracledb.DatabaseError as e:
        print(f"Database error: {e}")
        raise

# Authentication functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, user_type):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                user_id_var = cursor.var(oracledb.NUMBER)  # Create bind variable
                cursor.execute(
                    "INSERT INTO users (username, password, user_type) VALUES (:1, :2, :3) RETURNING user_id INTO :4",
                    [username, hash_password(password), user_type, user_id_var]
                )
                user_id = user_id_var.getvalue()[0]  
                conn.commit()
                return user_id
    except oracledb.IntegrityError:
        return None

def authenticate(username, password):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, user_type FROM users WHERE username = :1 AND password = :2",
                    [username, hash_password(password)]
                )
                result = cursor.fetchone()
                
                if result:
                    return {"user_id": result[0], "user_type": result[1]}
                return None
    except oracledb.DatabaseError:
        return None

# Customer functions
def register_customer(user_id, name, email, phone, address, street, city, id_number, license_number):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                # Create the bind variable for customer_id
                customer_id_var = cursor.var(oracledb.NUMBER)
                
                # Insert into customers table
                cursor.execute(
                    "INSERT INTO customer (user_id, name, email, phone, address, street, city, id_number, license) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9) RETURNING customer_id INTO :10",
                    [user_id, name, email, phone, address, street, city, id_number, license_number, customer_id_var]
                )
                
                customer_id = customer_id_var.getvalue()[0]  # Get the returned customer_id
                
                conn.commit()
                return customer_id
    except oracledb.DatabaseError as e:
        print(f"Error in register_customer: {e}")
        return None

def get_customer_id_by_user_id(user_id):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT customer_id FROM customer WHERE user_id = :1", [user_id])
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                return None
    except oracledb.DatabaseError:
        return None

def get_employee_id_by_user_id(user_id):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT emp_id FROM employee WHERE user_id = :1", [user_id])
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                return None
    except oracledb.DatabaseError:
        return None

def get_customer_info(customer_id):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT name, email, phone, address, street, city, id_number, license
                FROM customer
                WHERE customer_id = :1
                ''', [customer_id])
                
                result = cursor.fetchone()
                
                if result:
                    return {
                        "name": result[0],
                        "email": result[1],
                        "phone": result[2],
                        "address": result[3],
                        "street": result[4],
                        "city": result[5],
                        "id_number": result[6],
                        "license": result[7]
                    }
                return None
    except oracledb.DatabaseError as e:
        print(f"Error in get_customer_info: {e}")
        return None

def get_employee_info(emp_id):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT name, email, phone, address, street, city
                FROM employee
                WHERE emp_id = :1
                ''', [emp_id])
                
                result = cursor.fetchone()
                
                if result:
                    return {
                        "name": result[0],
                        "email": result[1],
                        "phone": result[2],
                        "address": result[3],
                        "street": result[4],
                        "city": result[5]
                    }
                return None
    except oracledb.DatabaseError as e:
        print(f"Error in get_employee_info: {e}")
        return None

def register_employee(user_id, name, email, phone, address, street, city):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                # Create bind variable for emp_id
                emp_id_var = cursor.var(oracledb.NUMBER)

                # Insert into employee table
                cursor.execute(
                    "INSERT INTO employee (user_id, name, email, phone, address, street, city) VALUES (:1, :2, :3, :4, :5, :6, :7) RETURNING emp_id INTO :8",
                    [user_id, name, email, phone, address, street, city, emp_id_var]
                )
                emp_id = emp_id_var.getvalue()[0]  # Get actual value

                conn.commit()
                return emp_id
    except oracledb.DatabaseError as e:
        print(f"Error in register_employee: {e}")
        return None

def get_available_cars():
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT c.car_id, c.model, c.plate_no, c.daily_price 
                FROM car c
                WHERE c.car_id NOT IN (
                    SELECT r.car_id 
                    FROM reserve r 
                    WHERE r.status = 'Active'
                )
                ORDER BY c.daily_price
                ''')
                
                columns = ['car_id', 'model', 'plate_no', 'daily_price']
                
                result = []
                for row in cursor:
                    result.append(dict(zip(columns, row)))
                
                return result
    except oracledb.DatabaseError as e:
        print(f"Error in get_available_cars: {e}")
        return []

def make_reservation(customer_id, car_id, pickup_day):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                # Create a bind variable for resv_id
                resv_id_var = cursor.var(oracledb.NUMBER)
                
                # Insert the reservation
                cursor.execute('''
                    INSERT INTO reserve 
                    (customer_id, car_id, pickup_day) 
                    VALUES (:1, :2, TO_DATE(:3, 'YYYY-MM-DD'))
                    RETURNING resv_id INTO :4
                ''', [customer_id, car_id, pickup_day, resv_id_var])
                
                resv_id = resv_id_var.getvalue()[0]
                
                # Get car price
                cursor.execute("SELECT daily_price FROM car WHERE car_id = :1", [car_id])
                daily_price, = cursor.fetchone()
                
                # Create payment record
                pay_id_var = cursor.var(oracledb.NUMBER)
                due_date = (datetime.datetime.strptime(pickup_day, '%Y-%m-%d') + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                
                cursor.execute('''
                    INSERT INTO payments
                    (customer_id, amount, due_date)
                    VALUES (:1, :2, TO_DATE(:3, 'YYYY-MM-DD'))
                    RETURNING pay_id INTO :4
                ''', [customer_id, daily_price, due_date, pay_id_var])
                
                conn.commit()
                return resv_id
    except oracledb.DatabaseError as e:
        print(f"Error in make_reservation: {e}")
        return None

def get_customer_reservations(customer_id):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT r.resv_id, c.model, c.plate_no, c.daily_price,
                       TO_CHAR(r.pickup_day, 'YYYY-MM-DD') as pickup_day,
                       TO_CHAR(r.reserve_date, 'YYYY-MM-DD') as reserve_date,
                       r.status
                FROM reserve r
                JOIN car c ON r.car_id = c.car_id
                WHERE r.customer_id = :1
                ORDER BY r.reserve_date DESC
                ''', [customer_id])
                
                columns = ['resv_id', 'model', 'plate_no', 'daily_price', 
                           'pickup_day', 'reserve_date', 'status']
                
                result = []
                for row in cursor:
                    result.append(dict(zip(columns, row)))
                
                return result
    except oracledb.DatabaseError as e:
        print(f"Error in get_customer_reservations: {e}")
        return []

def get_customer_payments(customer_id):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT p.pay_id, p.amount, 
                       TO_CHAR(p.pay_date, 'YYYY-MM-DD') as pay_date,
                       TO_CHAR(p.due_date, 'YYYY-MM-DD') as due_date,
                       p.method, p.pay_status,
                       NVL(e.name, 'Not Assigned') as employee_name
                FROM payments p
                LEFT JOIN employee e ON p.employee_id = e.emp_id
                WHERE p.customer_id = :1
                ORDER BY p.pay_date DESC
                ''', [customer_id])
                
                columns = ['pay_id', 'amount', 'pay_date', 'due_date', 
                           'method', 'pay_status', 'employee_name']
                
                result = []
                for row in cursor:
                    result.append(dict(zip(columns, row)))
                
                return result
    except oracledb.DatabaseError as e:
        print(f"Error in get_customer_payments: {e}")
        return []

def process_payment(pay_id, method, employee_id):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                # Update the payment record
                cursor.execute('''
                    UPDATE payments
                    SET method = :1,
                        pay_status = 'Paid',
                        employee_id = :2,
                        pay_date = CURRENT_DATE
                    WHERE pay_id = :3
                ''', [method, employee_id, pay_id])
                
                conn.commit()
                return True
    except oracledb.DatabaseError as e:
        print(f"Error in process_payment: {e}")
        return False

def get_pending_payments():
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT p.pay_id, c.name as customer_name, p.amount, 
                       TO_CHAR(p.pay_date, 'YYYY-MM-DD') as pay_date,
                       TO_CHAR(p.due_date, 'YYYY-MM-DD') as due_date,
                       p.pay_status
                FROM payments p
                JOIN customer c ON p.customer_id = c.customer_id
                WHERE p.pay_status = 'Pending'
                ORDER BY p.due_date
                ''')
                
                columns = ['pay_id', 'customer_name', 'amount', 'pay_date', 
                           'due_date', 'pay_status']
                
                result = []
                for row in cursor:
                    result.append(dict(zip(columns, row)))
                
                return result
    except oracledb.DatabaseError as e:
        print(f"Error in get_pending_payments: {e}")
        return []

def get_all_reservations():
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT r.resv_id, c.name as customer_name, 
                       car.model, car.plate_no,
                       TO_CHAR(r.pickup_day, 'YYYY-MM-DD') as pickup_day,
                       TO_CHAR(r.reserve_date, 'YYYY-MM-DD') as reserve_date,
                       r.status
                FROM reserve r
                JOIN customer c ON r.customer_id = c.customer_id
                JOIN car ON r.car_id = car.car_id
                ORDER BY r.reserve_date DESC
                ''')
                
                columns = ['resv_id', 'customer_name', 'model', 'plate_no', 
                           'pickup_day', 'reserve_date', 'status']
                
                result = []
                for row in cursor:
                    result.append(dict(zip(columns, row)))
                
                return result
    except oracledb.DatabaseError as e:
        print(f"Error in get_all_reservations: {e}")
        return []

def update_reservation_status(resv_id, status):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE reserve SET status = :1 WHERE resv_id = :2",
                    [status, resv_id]
                )
                conn.commit()
                return True
    except oracledb.DatabaseError as e:
        print(f"Error in update_reservation_status: {e}")
        return False

def add_car(model, plate_no, daily_price):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                # Create a bind variable for car_id
                car_id_var = cursor.var(oracledb.NUMBER)
                
                cursor.execute('''
                    INSERT INTO car 
                    (model, plate_no, daily_price) 
                    VALUES (:1, :2, :3)
                    RETURNING car_id INTO :4
                ''', [model, plate_no, daily_price, car_id_var])
                
                car_id = car_id_var.getvalue()[0]
                conn.commit()
                return car_id
    except oracledb.DatabaseError as e:
        print(f"Error in add_car: {e}")
        return None

def get_all_cars():
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT car_id, model, plate_no, daily_price
                FROM car
                ORDER BY model
                ''')
                
                columns = ['car_id', 'model', 'plate_no', 'daily_price']
                
                result = []
                for row in cursor:
                    result.append(dict(zip(columns, row)))
                
                return result
    except oracledb.DatabaseError as e:
        print(f"Error in get_all_cars: {e}")
        return []