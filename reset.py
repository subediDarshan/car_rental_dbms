import oracledb
import os

# Database configuration
DB_USER = os.getenv("DB_USER", "new_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "1521")
DB_SERVICE = os.getenv("DB_SERVICE", "XEPDB1")

def reset_database():
    try:
        with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}") as conn:
            with conn.cursor() as cursor:
                # First, drop all triggers
                try:
                    cursor.execute("""
                        BEGIN
                            FOR t IN (SELECT trigger_name FROM user_triggers) LOOP
                                EXECUTE IMMEDIATE 'DROP TRIGGER ' || t.trigger_name;
                            END LOOP;
                        END;
                    """)
                    print("Dropped all triggers")
                except oracledb.DatabaseError as e:
                    print(f"Error dropping triggers: {e}")

                # List of tables to drop in correct order (considering dependencies)
                tables = [
                    "PAYMENTS",
                    "RESERVE",
                    "CAR",
                    "EMPLOYEE",
                    "CUSTOMER",
                    "USERS"
                ]

                # Drop each table
                for table in tables:
                    try:
                        cursor.execute(f"DROP TABLE {table} CASCADE CONSTRAINTS PURGE")
                        print(f"Dropped table: {table}")
                    except oracledb.DatabaseError as e:
                        print(f"Error dropping table {table}: {e}")

                conn.commit()
                print("\nDatabase reset completed successfully!")

    except oracledb.DatabaseError as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Starting database reset...")
    reset_database()