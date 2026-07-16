import mysql.connector

def get_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="$Divya@1010",  
        database="ecommerce"
    )

    cursor = conn.cursor()
    cursor.execute("SET time_zone = '+05:30'")
    cursor.close()

    return conn