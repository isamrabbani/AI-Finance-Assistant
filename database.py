import mysql.connector

def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Isam@123",
        database="finance_db"
    )

    return connection


try:
    connection = get_db_connection()
    print("MySQL connection successful!")
    connection.close()

except mysql.connector.Error as error:
    print("MySQL connection failed:", error)