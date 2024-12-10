import mysql.connector

class Database:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print("Connection established")
        except mysql.connector.Error as err:
            print(f"Error: {err}")

    def cursor(self, dictionary=False):
        if not self.connection:
            raise ConnectionError("Database not connected")
        return self.connection.cursor(dictionary=dictionary)

    def execute_query(self, query, params=None):
        cursor = self.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None
        finally:
            cursor.close()

    def commit(self):
        if self.connection:
            self.connection.commit()

    def close(self):
        if self.connection:
            self.connection.close()