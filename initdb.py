import oracledb
import time
import getpass
import sys

def setup_database():
    """
    Sets up the Oracle database for the Car Rental System by creating all required objects.
    """
    print("\n=== Car Rental System - Oracle Database Setup ===\n")
    
    # Get connection credentials
    username = "new_user"
    password = "password"
    dsn = "localhost:1521/XEPDB1"
    
    try:
        print("\nConnecting to Oracle database...")
        connection = oracledb.connect(user=username, password=password, dsn=dsn)
        print("Connected successfully!")
        
        # Create a cursor
        cursor = connection.cursor()
        
        print("\nSetting up database objects...")
        
        # Create custom types for Address and Contact
        print("Creating object types...")
        try_execute(cursor, "DROP TYPE Address_Type FORCE")
        try_execute(cursor, "DROP TYPE Contact_Type FORCE")
        
        try_execute(cursor, """
        CREATE OR REPLACE TYPE Address_Type AS OBJECT (
            Street VARCHAR2(100),
            City VARCHAR2(50)
        )
        """)
        
        try_execute(cursor, """
        CREATE OR REPLACE TYPE Contact_Type AS OBJECT (
            Email VARCHAR2(100),
            Phone VARCHAR2(20)
        )
        """)
        
        # Drop existing tables if they exist
        print("Dropping existing tables...")
        tables = ["PAYMENTS", "RESERVE", "CUSTOMER", "CAR", "EMPLOYEE"]
        for table in tables:
            try_execute(cursor, f"DROP TABLE {table} CASCADE CONSTRAINTS")
        
        # Drop existing sequences if they exist
        print("Dropping existing sequences...")
        sequences = ["CUSTOMER_SEQ", "CAR_SEQ", "EMPLOYEE_SEQ", "RESERVE_SEQ", "PAYMENT_SEQ"]
        for seq in sequences:
            try_execute(cursor, f"DROP SEQUENCE {seq}")
        
        # Create sequences for auto-incrementing IDs
        print("Creating sequences...")
        try_execute(cursor, "CREATE SEQUENCE customer_seq START WITH 1 INCREMENT BY 1")
        try_execute(cursor, "CREATE SEQUENCE car_seq START WITH 1 INCREMENT BY 1")
        try_execute(cursor, "CREATE SEQUENCE employee_seq START WITH 1 INCREMENT BY 1")
        try_execute(cursor, "CREATE SEQUENCE reserve_seq START WITH 1 INCREMENT BY 1")
        try_execute(cursor, "CREATE SEQUENCE payment_seq START WITH 1 INCREMENT BY 1")
        
        # Create tables
        print("Creating tables...")
        
        # Create Customer table
        try_execute(cursor, """
        CREATE TABLE Customer (
            ID NUMBER PRIMARY KEY,
            Name VARCHAR2(100) NOT NULL,
            Email VARCHAR2(100),
            Phone VARCHAR2(20),
            License VARCHAR2(20) UNIQUE NOT NULL,
            Address Address_Type
        )
        """)
        
        # Create Car table
        try_execute(cursor, """
        CREATE TABLE Car (
            Car_ID NUMBER PRIMARY KEY,
            Plate_No VARCHAR2(20) UNIQUE NOT NULL,
            Model VARCHAR2(100) NOT NULL,
            Daily_Price NUMBER(10,2) NOT NULL
        )
        """)
        
        # Create Employee table
        try_execute(cursor, """
        CREATE TABLE Employee (
            Emp_ID NUMBER PRIMARY KEY,
            Name VARCHAR2(100) NOT NULL,
            Address Address_Type,
            Contact Contact_Type
        )
        """)
        
        # Create Reserve table
        try_execute(cursor, """
        CREATE TABLE Reserve (
            ReserveID NUMBER PRIMARY KEY,
            Customer_ID NUMBER NOT NULL,
            Car_ID NUMBER NOT NULL,
            Pickup_day DATE NOT NULL,
            reserve_date DATE DEFAULT SYSDATE,
            Status VARCHAR2(20) CHECK (Status IN ('Active', 'Pending', 'Completed', 'Cancelled')) DEFAULT 'Pending',
            FOREIGN KEY (Customer_ID) REFERENCES Customer(ID),
            FOREIGN KEY (Car_ID) REFERENCES Car(Car_ID)
        )
        """)
        
        # Create Payments table
        try_execute(cursor, """
        CREATE TABLE Payments (
            Pay_ID NUMBER PRIMARY KEY,
            Customer_ID NUMBER NOT NULL,
            Employee_ID NUMBER NOT NULL,
            Amount NUMBER(10,2) NOT NULL,
            Due DATE NOT NULL,
            Method VARCHAR2(50) CHECK (Method IN ('Credit Card', 'Cash', 'Bank Transfer', 'Cheque')),
            Pay_status VARCHAR2(20) CHECK (Pay_status IN ('Paid', 'Pending', 'Overdue')),
            FOREIGN KEY (Customer_ID) REFERENCES Customer(ID),
            FOREIGN KEY (Employee_ID) REFERENCES Employee(Emp_ID)
        )
        """)
        
        # Insert sample data if requested
        insert_sample = input("\nDo you want to insert sample data? (y/n): ").lower()
        if insert_sample == 'y' or insert_sample == 'yes':
            print("Inserting sample data...")
            
            # Insert sample customers
            try_execute(cursor, """
            INSERT INTO Customer VALUES (
                customer_seq.NEXTVAL, 
                'John Smith', 
                'john.smith@email.com', 
                '555-123-4567', 
                'DL12345678', 
                Address_Type('123 Main St', 'New York')
            )
            """)
            
            try_execute(cursor, """
            INSERT INTO Customer VALUES (
                customer_seq.NEXTVAL, 
                'Jane Doe', 
                'jane.doe@email.com', 
                '555-987-6543', 
                'DL87654321', 
                Address_Type('456 Oak Ave', 'Chicago')
            )
            """)
            
            try_execute(cursor, """
            INSERT INTO Customer VALUES (
                customer_seq.NEXTVAL, 
                'Michael Johnson', 
                'michael.j@email.com', 
                '555-456-7890', 
                'DL45678901', 
                Address_Type('789 Pine Rd', 'Los Angeles')
            )
            """)
            
            # Insert sample cars
            try_execute(cursor, """
            INSERT INTO Car VALUES (
                car_seq.NEXTVAL,
                'ABC123',
                'Toyota Camry',
                65.00
            )
            """)
            
            try_execute(cursor, """
            INSERT INTO Car VALUES (
                car_seq.NEXTVAL,
                'XYZ789',
                'Honda Civic',
                55.00
            )
            """)
            
            try_execute(cursor, """
            INSERT INTO Car VALUES (
                car_seq.NEXTVAL,
                'DEF456',
                'Ford Explorer',
                85.00
            )
            """)
            
            try_execute(cursor, """
            INSERT INTO Car VALUES (
                car_seq.NEXTVAL,
                'GHI789',
                'Chevrolet Malibu',
                60.00
            )
            """)
            
            # Insert sample employees
            try_execute(cursor, """
            INSERT INTO Employee VALUES (
                employee_seq.NEXTVAL,
                'Emily Wilson',
                Address_Type('101 First Ave', 'New York'),
                Contact_Type('emily.w@company.com', '555-222-3333')
            )
            """)
            
            try_execute(cursor, """
            INSERT INTO Employee VALUES (
                employee_seq.NEXTVAL,
                'Robert Brown',
                Address_Type('202 Second St', 'Chicago'),
                Contact_Type('robert.b@company.com', '555-444-5555')
            )
            """)
            
            # Insert sample reservations
            try_execute(cursor, """
            INSERT INTO Reserve VALUES (
                reserve_seq.NEXTVAL,
                1,
                1,
                TO_DATE('2025-05-20', 'YYYY-MM-DD'),
                SYSDATE,
                'Active'
            )
            """)
            
            try_execute(cursor, """
            INSERT INTO Reserve VALUES (
                reserve_seq.NEXTVAL,
                2,
                2,
                TO_DATE('2025-05-25', 'YYYY-MM-DD'),
                SYSDATE,
                'Pending'
            )
            """)
            
            # Insert sample payments
            try_execute(cursor, """
            INSERT INTO Payments VALUES (
                payment_seq.NEXTVAL,
                1,
                1,
                195.00,
                TO_DATE('2025-05-23', 'YYYY-MM-DD'),
                'Credit Card',
                'Pending'
            )
            """)
            
            try_execute(cursor, """
            INSERT INTO Payments VALUES (
                payment_seq.NEXTVAL,
                2,
                2,
                165.00,
                TO_DATE('2025-05-28', 'YYYY-MM-DD'),
                'Cash',
                'Paid'
            )
            """)
        
        # Commit all changes
        connection.commit()
        
        print("\n=== Database setup completed successfully! ===")
        
        # Print table counts
        print("\nDatabase objects created:")
        
        cursor.execute("SELECT table_name FROM user_tables WHERE table_name IN ('CUSTOMER', 'CAR', 'EMPLOYEE', 'RESERVE', 'PAYMENTS')")
        tables = cursor.fetchall()
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"- {table[0]}: {count} records")
        
        cursor.close()
        connection.close()
        
    except oracledb.Error as error:
        print(f"Oracle error: {error}")
    except Exception as error:
        print(f"Error: {error}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            print("\nConnection closed.")

def try_execute(cursor, sql):
    """
    Executes SQL statement and handles common errors.
    """
    try:
        cursor.execute(sql)
    except oracledb.Error as e:
        error_obj, = e.args
        # Ignore "does not exist" errors when dropping objects
        if error_obj.code in (942, 1918, 4043):  # ORA-00942 (table doesn't exist), ORA-01918 (sequence doesn't exist), ORA-04043 (object doesn't exist)
            pass
        else:
            print(f"Error executing: {sql[:60]}...")
            print(f"Oracle Error: {error_obj.code}: {error_obj.message}")

if __name__ == "__main__":
    try:
        setup_database()
    except KeyboardInterrupt:
        print("\nSetup interrupted by user.")
        sys.exit(1)