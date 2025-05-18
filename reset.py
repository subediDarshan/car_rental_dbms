import oracledb
import getpass
import sys

def reset_database():
    """
    Deletes all tables and objects from the Oracle database for the Car Rental System.
    """
    print("\n=== Car Rental System - Oracle Database Reset ===\n")
    
    username = "new_user"
    password = "password"
    dsn = "localhost:1521/XEPDB1"
    
    try:
        print("\nConnecting to Oracle database...")
        connection = oracledb.connect(user=username, password=password, dsn=dsn)
        print("Connected successfully!")
        
        cursor = connection.cursor()
        
        print("\nDropping database objects...")
        
        # Drop tables
        tables = ["PAYMENTS", "RESERVE", "CUSTOMER", "CAR", "EMPLOYEE"]
        for table in tables:
            try_execute(cursor, f"DROP TABLE {table} CASCADE CONSTRAINTS")
            
        # Drop sequences
        sequences = ["CUSTOMER_SEQ", "CAR_SEQ", "EMPLOYEE_SEQ", "RESERVE_SEQ", "PAYMENT_SEQ"]
        for seq in sequences:
            try_execute(cursor, f"DROP SEQUENCE {seq}")
            
        # Drop custom types
        types = ["Address_Type", "Contact_Type"]
        for type_name in types:
            try_execute(cursor, f"DROP TYPE {type_name} FORCE")
            
        connection.commit()
        print("\n=== Database reset completed successfully! ===")
        
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
        if error_obj.code in (942, 1918, 4043):  # Ignore "does not exist" errors
            pass
        else:
            print(f"Error executing: {sql[:60]}...")
            print(f"Oracle Error: {error_obj.code}: {error_obj.message}")

if __name__ == "__main__":
    try:
        reset_database()
    except KeyboardInterrupt:
        print("\nReset interrupted by user.")
        sys.exit(1)