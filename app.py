import streamlit as st
import pandas as pd
import oracledb
import hashlib
import datetime
from datetime import timedelta  # Add this import
import os
import time

# Database configuration
DB_USER = os.getenv("DB_USER", "new_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
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
                
                # Add this in init_db() function after other trigger creation
                try:
                    cursor.execute("""
                    CREATE OR REPLACE TRIGGER payment_status_trigger
                    FOR UPDATE OF pay_status ON payments
                    COMPOUND TRIGGER
                    
                    -- Global variables for the trigger
                    v_customer_id NUMBER;
                    v_pay_id NUMBER;
                    
                    -- BEFORE EACH ROW section to capture values
                    BEFORE EACH ROW IS
                    BEGIN
                        IF :NEW.pay_status = 'Paid' THEN
                            v_customer_id := :NEW.customer_id;
                            v_pay_id := :NEW.pay_id;
                        END IF;
                    END BEFORE EACH ROW;
                    
                    -- AFTER STATEMENT section to perform the update
                    AFTER STATEMENT IS
                    BEGIN
                        IF v_customer_id IS NOT NULL THEN
                            UPDATE reserve r
                            SET r.status = 'Active'
                            WHERE r.customer_id = v_customer_id
                            AND r.status = 'Pending'
                            AND EXISTS (
                                SELECT 1 
                                FROM payments p 
                                WHERE p.customer_id = r.customer_id 
                                AND p.pay_id = v_pay_id
                            );
                        END IF;
                    END AFTER STATEMENT;
                    
                    END payment_status_trigger;
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
                
                # Add PL/SQL procedure for updating reservation status
                try:#PLSQL procedure is applied
                    cursor.execute("""
                    CREATE OR REPLACE PROCEDURE update_reservation_status_proc (
                        p_resv_id IN NUMBER,
                        p_status IN VARCHAR2,
                        p_success OUT NUMBER
                    ) IS
                    BEGIN
                        UPDATE reserve 
                        SET status = p_status
                        WHERE resv_id = p_resv_id;
                        
                        IF SQL%ROWCOUNT > 0 THEN
                            p_success := 1;
                            COMMIT;
                        ELSE
                            p_success := 0;
                            ROLLBACK;
                        END IF;
                    EXCEPTION
                        WHEN OTHERS THEN
                            p_success := 0;
                            ROLLBACK;
                    END;
                    """)
                except oracledb.DatabaseError as e:
                    error, = e.args
                    if error.code != 955:  # Procedure already exists
                        raise
                
                # Add PL/SQL function for getting customer info
                try:
                    cursor.execute("""
                    CREATE OR REPLACE FUNCTION get_customer_info_func (
                        p_customer_id IN NUMBER
                    ) RETURN SYS_REFCURSOR IS
                        v_result SYS_REFCURSOR;
                    BEGIN
                        OPEN v_result FOR
                            SELECT name, email, phone, address, street, city, 
                                   id_number, license
                            FROM customer
                            WHERE customer_id = p_customer_id;
                        RETURN v_result;
                    END;
                    """)
                except oracledb.DatabaseError as e:
                    error, = e.args
                    if error.code != 955:  # Function already exists
                        raise
                
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
#PLSQL function is applied here

def get_customer_info(customer_id):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                # Call the PL/SQL function using REF CURSOR
                ref_cursor = cursor.callfunc(
                    "get_customer_info_func",
                    oracledb.CURSOR,
                    [customer_id]
                )
                
                # Fetch result from the REF CURSOR
                result = ref_cursor.fetchone()
                
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

#Sub query applied here

def get_available_cars():
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                # Simple subquery to get available cars
                cursor.execute('''
                SELECT 
                    car_id,
                    model,
                    plate_no,
                    daily_price,
                    (SELECT COUNT(*) 
                     FROM reserve r 
                     WHERE r.car_id = c.car_id 
                     AND r.status = 'Active') as active_bookings
                FROM car c
                WHERE (SELECT COUNT(*) 
                      FROM reserve r 
                      WHERE r.car_id = c.car_id 
                      AND r.status = 'Active') = 0
                ORDER BY daily_price
                ''')
                
                columns = ['car_id', 'model', 'plate_no', 'daily_price', 'active_bookings']
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

#Join is applied
def get_customer_reservations(customer_id):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                SELECT 
                    r.resv_id,
                    r.car_id,
                    c.model,
                    c.plate_no,
                    c.daily_price,
                    TO_CHAR(r.pickup_day, 'YYYY-MM-DD') as pickup_day,
                    TO_CHAR(r.reserve_date, 'YYYY-MM-DD') as reserve_date,
                    r.status
                FROM reserve r
                JOIN car c ON r.car_id = c.car_id
                WHERE r.customer_id = :1
                ORDER BY r.pickup_day DESC
                ''', [customer_id])
                
                columns = ['resv_id', 'car_id', 'model', 'plate_no', 'daily_price', 
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

#PLSQL Trigger applied here
def process_payment(pay_id, method, employee_id):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                # Simple update - trigger will handle reservation status
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

#PLSQL PROCEDURE IS APPLIED
def update_reservation_status(resv_id, status):
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn) as conn:
            with conn.cursor() as cursor:
                # Create OUT parameter for success flag
                success_var = cursor.var(oracledb.NUMBER)
                
                # Call the PL/SQL procedure
                cursor.callproc("update_reservation_status_proc", 
                              [resv_id, status, success_var])
                
                # Commit the transaction
                conn.commit()
                
                # Check if update was successful
                return success_var.getvalue() == 1
                
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





def main():
    # Initialize the database
    try:
        init_db()
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
    
    # Set page config
    st.set_page_config(
        page_title="Car Rental System",
        page_icon="🚗",
        layout="wide"
    )
    
    # Session state initialization
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.user_type = None
        st.session_state.customer_id = None
        st.session_state.employee_id = None
        st.session_state.current_page = "login"
    
    # Sidebar for navigation when logged in
    if st.session_state.logged_in:
        with st.sidebar:
            st.title("Car Rental System")
            st.write(f"Welcome, {st.session_state.user_type}!")
            
            if st.session_state.user_type == "Customer":
                customer_info = get_customer_info(st.session_state.customer_id)
                if customer_info:
                    st.write(f"Name: {customer_info['name']}")
                
                st.button("Dashboard", on_click=lambda: set_page("customer_dashboard"))
                st.button("Make Reservation", on_click=lambda: set_page("make_reservation"))
                st.button("My Reservations", on_click=lambda: set_page("customer_reservations"))
                st.button("My Payments", on_click=lambda: set_page("customer_payments"))
                st.button("Profile", on_click=lambda: set_page("customer_profile"))
            
            elif st.session_state.user_type == "Employee":
                employee_info = get_employee_info(st.session_state.employee_id)
                if employee_info:
                    st.write(f"Name: {employee_info['name']}")
                
                st.button("Dashboard", on_click=lambda: set_page("employee_dashboard"))
                st.button("Manage Cars", on_click=lambda: set_page("manage_cars"))
                st.button("Process Payments", on_click=lambda: set_page("process_payments"))
                st.button("Manage Reservations", on_click=lambda: set_page("manage_reservations"))
                st.button("Profile", on_click=lambda: set_page("employee_profile"))
            
            if st.button("Logout"):
                logout()
    
    # Render the appropriate page
    if not st.session_state.logged_in:
        render_login_page()
    else:
        if st.session_state.current_page == "login":
            if st.session_state.user_type == "Customer":
                set_page("customer_dashboard")
            else:
                set_page("employee_dashboard")
        elif st.session_state.current_page == "customer_dashboard":
            render_customer_dashboard()
        elif st.session_state.current_page == "make_reservation":
            render_make_reservation()
        elif st.session_state.current_page == "customer_reservations":
            render_customer_reservations()
        elif st.session_state.current_page == "customer_payments":
            render_customer_payments()
        elif st.session_state.current_page == "customer_profile":
            render_customer_profile()
        elif st.session_state.current_page == "employee_dashboard":
            render_employee_dashboard()
        elif st.session_state.current_page == "manage_cars":
            render_manage_cars()
        elif st.session_state.current_page == "process_payments":
            render_process_payments()
        elif st.session_state.current_page == "manage_reservations":
            render_manage_reservations()
        elif st.session_state.current_page == "employee_profile":
            render_employee_profile()
        elif st.session_state.current_page == "register":
            render_register_page()

def set_page(page):
    st.session_state.current_page = page

def logout():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_type = None
    st.session_state.customer_id = None
    st.session_state.employee_id = None
    st.session_state.current_page = "login"
    st.rerun()


def render_register_page():
    st.title("Register")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        user_type = st.selectbox("Register as", ["Customer", "Employee"])
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        conf_password = st.text_input("Confirm Password", type="password")
        
        st.write("Personal Information")
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        address = st.text_input("Address")
        street = st.text_input("Street")
        city = st.text_input("City")
        
        if user_type == "Customer":
            id_number = st.text_input("ID Number")
            license_number = st.text_input("Driver's License Number")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Register"):
                if not username or not password or not conf_password or not name:
                    st.warning("Please fill in all required fields")
                elif password != conf_password:
                    st.error("Passwords do not match")
                else:
                    user_id = register_user(username, password, user_type)
                    
                    if user_id:
                        if user_type == "Customer":
                            customer_id = register_customer(user_id, name, email, phone, address, street, city, id_number, license_number)
                            if customer_id:
                                st.success("Registration successful! You can now login.")
                                st.session_state.current_page = "login"
                                st.rerun()
                            else:
                                st.error("Failed to create customer record")
                        else:  # Employee
                            emp_id = register_employee(user_id, name, email, phone, address, street, city)
                            if emp_id:
                                st.success("Registration successful! You can now login.")
                                st.session_state.current_page = "login"
                                st.rerun()
                            else:
                                st.error("Failed to create employee record")
                    else:
                        st.error("Username already exists")
        
        with col2:
            if st.button("Back to Login"):
                st.session_state.current_page = "login"
                st.rerun()


def render_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("Car Rental System")
        
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.subheader("Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", key="login_button"):
                if username and password:
                    user_info = authenticate(username, password)
                    if user_info:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_info["user_id"]
                        st.session_state.user_type = user_info["user_type"]
                        
                        if user_info["user_type"] == "Customer":
                            customer_id = get_customer_id_by_user_id(user_info["user_id"])
                            if customer_id:
                                st.session_state.customer_id = customer_id
                                st.rerun()
                            else:
                                st.error("Customer record not found. Please contact support.")
                        elif user_info["user_type"] == "Employee":
                            employee_id = get_employee_id_by_user_id(user_info["user_id"])
                            if employee_id:
                                st.session_state.employee_id = employee_id
                                st.rerun()
                            else:
                                st.error("Employee record not found. Please contact support.")
                    else:
                        st.error("Invalid username or password")
                else:
                    st.warning("Please enter both username and password")
        
        with tab2:
            st.subheader("Register")
            user_type = st.selectbox("Register as", ["Customer", "Employee"])
            username = st.text_input("Username", key="reg_username")
            password = st.text_input("Password", type="password", key="reg_password")
            conf_password = st.text_input("Confirm Password", type="password", key="reg_conf_password")
            
            st.write("Personal Information")
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            address = st.text_input("Address")
            street = st.text_input("Street")
            city = st.text_input("City")
            
            if user_type == "Customer":
                id_number = st.text_input("ID Number")
                license_number = st.text_input("Driver's License Number")
            
            if st.button("Register"):
                if not username or not password or not conf_password or not name:
                    st.warning("Please fill in all required fields")
                elif password != conf_password:
                    st.error("Passwords do not match")
                else:
                    user_id = register_user(username, password, user_type)
                    
                    if user_id:
                        if user_type == "Customer":
                            customer_id = register_customer(user_id, name, email, phone, address, street, city, id_number, license_number)
                            if customer_id:
                                st.success("Registration successful! You can now login.")
                                st.session_state.current_page = "login"
                                st.rerun()
                            else:
                                st.error("Failed to create customer record")
                        else:  # Employee
                            emp_id = register_employee(user_id, name, email, phone, address, street, city)
                            if emp_id:
                                st.success("Registration successful! You can now login.")
                                st.session_state.current_page = "login"
                                st.rerun()
                            else:
                                st.error("Failed to create employee record")
                    else:
                        st.error("Username already exists")

def render_customer_dashboard():
    st.title("Customer Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Quick Stats")
        
        # Get customer reservations
        reservations = get_customer_reservations(st.session_state.customer_id)
        active_reservations = [r for r in reservations if r["status"] == "Active"]
        pending_reservations = [r for r in reservations if r["status"] == "Pending"]
        
        # Get customer payments
        payments = get_customer_payments(st.session_state.customer_id)
        pending_payments = [p for p in payments if p["pay_status"] == "Pending"]
        
        # Display quick stats
        st.metric("Active Reservations", len(active_reservations))
        st.metric("Pending Reservations", len(pending_reservations))
        st.metric("Pending Payments", len(pending_payments))
    
    with col2:
        st.subheader("Available Cars")
        cars = get_available_cars()
        
        if cars:
            cars_df = pd.DataFrame(cars)
            st.dataframe(cars_df[["model", "plate_no", "daily_price"]], hide_index=True)
            
            if st.button("Make a Reservation"):
                set_page("make_reservation")
        else:
            st.info("No cars available at the moment")

def render_make_reservation():
    st.title("Make a Reservation")
    
    # Get available cars
    cars = get_available_cars()
    
    if not cars:
        st.info("No cars available at the moment")
        return
    
    # Create a dataframe for display
    cars_df = pd.DataFrame(cars)
    
    # Display cars for selection
    st.subheader("Available Cars")
    st.dataframe(cars_df[["model", "plate_no", "daily_price"]], hide_index=True)
    
    # Car selection
    car_options = {f"{car['model']} ({car['plate_no']}) - ${car['daily_price']}/day": car["car_id"] for car in cars}
    selected_car = st.selectbox("Select a car", list(car_options.keys()))
    
    # Date selection for pickup
    min_date = datetime.date.today() + timedelta(days=1)
    pickup_date = st.date_input("Select pickup date", min_value=min_date, value=min_date)
    
    # Submit reservation
    if st.button("Submit Reservation"):
        if selected_car and pickup_date:
            car_id = car_options[selected_car]
            pickup_str = pickup_date.strftime("%Y-%m-%d")
            
            reservation_id = make_reservation(st.session_state.customer_id, car_id, pickup_str)
            
            if reservation_id:
                st.success(f"Reservation successful! Your reservation ID is {reservation_id}")
                st.info("Please make the payment before the pickup date to confirm your reservation")
                
                if st.button("View My Reservations"):
                    set_page("customer_reservations")
            else:
                st.error("Failed to make reservation. Please try again.")

def render_customer_reservations():
    st.title("My Reservations")
    
    # Get customer reservations
    reservations = get_customer_reservations(st.session_state.customer_id)
    
    if not reservations:
        st.info("You have no reservations yet")
        return
    
    # Create dataframe for display
    reservations_df = pd.DataFrame(reservations)
    
    # Display reservations with columns we know exist
    display_columns = ["resv_id", "model", "plate_no", "daily_price", 
                      "pickup_day", "reserve_date", "status"]
    st.dataframe(reservations_df[display_columns], hide_index=True)
    
    # Allow cancellation of pending reservations
    st.subheader("Cancel Reservation")
    
    pending_reservations = [r for r in reservations if r["status"] == "Pending"]
    
    if pending_reservations:
        cancel_options = {f"ID {r['resv_id']} - {r['model']} ({r['pickup_day']})": r["resv_id"] for r in pending_reservations}
        selected_reservation = st.selectbox("Select reservation to cancel", list(cancel_options.keys()))
        
        if st.button("Cancel Selected Reservation"):
            resv_id = cancel_options[selected_reservation]
            success = update_reservation_status(resv_id, "Cancelled")
            
            if success:
                st.success("Reservation cancelled successfully")
                st.rerun()
            else:
                st.error("Failed to cancel reservation")
    else:
        st.info("No pending reservations available to cancel")

def render_customer_payments():
    st.title("My Payments")
    
    # Get customer payments
    payments = get_customer_payments(st.session_state.customer_id)
    
    if not payments:
        st.info("You have no payment records yet")
        return
    
    # Create dataframe for display
    payments_df = pd.DataFrame(payments)
    
    # Display payments
    st.dataframe(
        payments_df[["pay_id", "amount", "pay_date", "due_date", "method", "pay_status", "employee_name"]],
        hide_index=True
    )
    
    # Highlight pending payments
    pending_payments = [p for p in payments if p["pay_status"] == "Pending"]
    
    if pending_payments:
        st.warning(f"You have {len(pending_payments)} pending payment(s). Please visit our office to complete your payments.")

def render_customer_profile():
    st.title("My Profile")
    
    # Get customer info
    customer_info = get_customer_info(st.session_state.customer_id)
    
    if not customer_info:
        st.error("Could not retrieve profile information")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Personal Information")
        st.write(f"**Name:** {customer_info['name']}")
        st.write(f"**Email:** {customer_info['email']}")
        st.write(f"**Phone:** {customer_info['phone']}")
        
    with col2:
        st.subheader("Address")
        st.write(f"**Address:** {customer_info['address']}")
        st.write(f"**Street:** {customer_info['street']}")
        st.write(f"**City:** {customer_info['city']}")
    
    st.subheader("Identification")
    st.write(f"**ID Number:** {customer_info['id_number']}")
    st.write(f"**Driver's License:** {customer_info['license']}")
    
    # Note: Profile editing functionality could be added here in the future

def render_employee_dashboard():
    st.title("Employee Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Quick Stats")
        
        # Get all reservations
        reservations = get_all_reservations()
        active_reservations = [r for r in reservations if r["status"] == "Active"]
        pending_reservations = [r for r in reservations if r["status"] == "Pending"]
        
        # Get pending payments
        pending_payments = get_pending_payments()
        
        # Get car count
        cars = get_all_cars()
        available_cars = get_available_cars()
        
        # Display quick stats
        st.metric("Active Reservations", len(active_reservations))
        st.metric("Pending Reservations", len(pending_reservations))
        st.metric("Pending Payments", len(pending_payments))
        st.metric("Available Cars", len(available_cars), f"{len(available_cars)}/{len(cars)}")
    
    with col2:
        st.subheader("Recent Reservations")
        
        if reservations:
            recent_df = pd.DataFrame(reservations[:5])
            st.dataframe(recent_df[["customer_name", "model", "pickup_day", "status"]], hide_index=True)
        else:
            st.info("No reservations found")
        
        st.subheader("Pending Payments")
        
        if pending_payments:
            payments_df = pd.DataFrame(pending_payments[:5])
            st.dataframe(payments_df[["customer_name", "amount", "due_date"]], hide_index=True)
        else:
            st.info("No pending payments")

def render_manage_cars():
    st.title("Manage Cars")
    
    tab1, tab2 = st.tabs(["View Cars", "Add New Car"])
    
    with tab1:
        cars = get_all_cars()
        
        if cars:
            cars_df = pd.DataFrame(cars)
            st.dataframe(cars_df, hide_index=True)
        else:
            st.info("No cars found in the database")
    
    with tab2:
        st.subheader("Add New Car")
        
        model = st.text_input("Car Model")
        plate_no = st.text_input("License Plate Number")
        daily_price = st.number_input("Daily Rental Price ($)", min_value=0.0, step=5.0)
        
        if st.button("Add Car"):
            if model and plate_no and daily_price > 0:
                car_id = add_car(model, plate_no, daily_price)
                
                if car_id:
                    st.success(f"Car added successfully with ID: {car_id}")
                    st.rerun()
                else:
                    st.error("Failed to add car. The license plate might already be in use.")
            else:
                st.warning("Please fill in all fields")

def render_process_payments():
    st.title("Process Payments")
    
    # Get pending payments
    pending_payments = get_pending_payments()
    
    if not pending_payments:
        st.info("No pending payments to process")
        return
    
    # Display pending payments
    st.subheader("Pending Payments")
    payments_df = pd.DataFrame(pending_payments)
    st.dataframe(payments_df, hide_index=True)
    
    # Payment processing form
    st.subheader("Process Payment")
    
    payment_options = {f"ID {p['pay_id']} - {p['customer_name']} (${p['amount']})": p["pay_id"] for p in pending_payments}
    selected_payment = st.selectbox("Select payment to process", list(payment_options.keys()))
    
    payment_method = st.selectbox("Payment Method", ["Cash", "Credit Card", "Debit Card", "Bank Transfer"])
    
    if st.button("Process Payment"):
        pay_id = payment_options[selected_payment]
        success = process_payment(pay_id, payment_method, st.session_state.employee_id)
        
        if success:
            st.success("Payment processed successfully")
            st.rerun()
        else:
            st.error("Failed to process payment")

def render_manage_reservations():
    st.title("Manage Reservations")
    
    # Get all reservations
    reservations = get_all_reservations()
    
    if not reservations:
        st.info("No reservations found")
        return
    
    # Filter options
    status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Active", "Completed", "Cancelled"])
    
    # Apply filters
    filtered_reservations = reservations
    if status_filter != "All":
        filtered_reservations = [r for r in reservations if r["status"] == status_filter]
    
    # Display reservations
    if filtered_reservations:
        reservations_df = pd.DataFrame(filtered_reservations)
        st.dataframe(reservations_df, hide_index=True)
    else:
        st.info(f"No reservations with status '{status_filter}'")
    
    # Reservation management form
    st.subheader("Update Reservation Status")
    
    updatable_reservations = [r for r in reservations if r["status"] in ["Pending", "Active"]]
    
    if updatable_reservations:
        reservation_options = {f"ID {r['resv_id']} - {r['customer_name']} ({r['model']})": r["resv_id"] for r in updatable_reservations}
        selected_reservation = st.selectbox("Select reservation", list(reservation_options.keys()))
        
        # Find current status
        current_status = next((r["status"] for r in updatable_reservations if r["resv_id"] == reservation_options[selected_reservation]), None)
        
        # Determine available status options based on current status
        status_options = []
        if current_status == "Pending":
            status_options = ["Active", "Cancelled"]
        elif current_status == "Active":
            status_options = ["Completed", "Cancelled"]
        
        new_status = st.selectbox("New Status", status_options)
        
        if st.button("Update Status"):
            resv_id = reservation_options[selected_reservation]
            success = update_reservation_status(resv_id, new_status)
            
            if success:
                st.success(f"Reservation status updated to {new_status}")
                st.rerun()
            else:
                st.error("Failed to update reservation status")
    else:
        st.info("No reservations available for status update")

def render_employee_profile():
    st.title("Employee Profile")
    
    # Get employee info
    employee_info = get_employee_info(st.session_state.employee_id)
    
    if not employee_info:
        st.error("Could not retrieve profile information")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Personal Information")
        st.write(f"**Name:** {employee_info['name']}")
        st.write(f"**Email:** {employee_info['email']}")
        st.write(f"**Phone:** {employee_info['phone']}")
        
    with col2:
        st.subheader("Address")
        st.write(f"**Address:** {employee_info['address']}")
        st.write(f"**Street:** {employee_info['street']}")
        st.write(f"**City:** {employee_info['city']}")

if __name__ == "__main__":
    main()