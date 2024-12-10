import random
import mysql.connector
from math import radians, sin, cos, sqrt, atan2

class Database:
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.conn = None

    def connect(self):
        try:
            self.conn = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=True
            )
            if self.conn.is_connected():
                print("Connection Established")
            return self.conn
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None

    def close(self):
        if self.conn:
            self.conn.close()

class Game:
    def __init__(self):
        self.db = Database('localhost', 3306, 'root', '12345', 'flight_path')
        self.player_id = None

    def start_game(self):
        conn = self.db.connect()
        if not conn:
            print("Database connection failed.")
            return

        cursor = conn.cursor()
        try:
            player_name = input("Enter your name: ")
            print(f"Welcome, {player_name}!")
            cursor.execute(
                """
                INSERT INTO player (
                    screen_name, fuel_amount, total_money, cargo_collected, 
                    start_location, destination, end_location
                ) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (player_name, 3000, 0, 0, 'LEMD', 'LIPE', 'LEMD')
            )
            conn.commit()
            cursor.execute("SELECT LAST_INSERT_ID()")
            self.player_id = int(cursor.fetchone()[0])
            print(f"Player created with ID: {self.player_id}")
        finally:
            cursor.close()
            self.db.close()

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius in kilometers
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    def get_airports_with_distances(self):
        conn = self.db.connect()
        if not conn:
            print("Database connection failed.")
            return

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT end_location, latitude_deg, longitude_deg
                FROM player
                JOIN new_airports ON player.end_location = new_airports.airport_code
                WHERE player.player_id = %s
                """,
                (self.player_id,)
            )
            player_location = cursor.fetchone()

            if not player_location:
                print(f"No location data found for player_id {self.player_id}.")
                return

            end_lat = float(player_location["latitude_deg"])
            end_lon = float(player_location["longitude_deg"])

            cursor.execute("SELECT airport_code, airport_name, latitude_deg, longitude_deg FROM new_airports")
            airports = cursor.fetchall()

            airport_distances = []
            for airport in airports:
                lat = float(airport["latitude_deg"])
                lon = float(airport["longitude_deg"])
                distance = self.calculate_distance(end_lat, end_lon, lat, lon)
                airport_distances.append((airport["airport_code"], airport["airport_name"], distance))

            airport_distances.sort(key=lambda x: x[2])
            print(f"Distances from {player_location['end_location']} to other airports:")
            for code, name, dist in airport_distances:
                print(f"{code}: {dist:.2f} km")
        finally:
            cursor.close()
            self.db.close()

    def set_unfavorable_weather(self):
        conn = self.db.connect()
        if not conn:
            print("Database connection failed.")
            return

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT airport_code FROM new_airports")
            airport_codes = [row[0] for row in cursor.fetchall()]

            unfavorable_airports = random.sample(airport_codes, 3)
            cursor.executemany(
                "UPDATE new_airports SET high_consumption = 1 WHERE airport_code = %s",
                [(airport,) for airport in unfavorable_airports]
            )
            conn.commit()

            cursor.execute(
                "SELECT airport_code, airport_name FROM new_airports WHERE high_consumption = 1"
            )
            print("Airports with unfavorable weather:")
            for airport in cursor.fetchall():
                print(f" - {airport[0]} ({airport[1]}) - Fuel consumption increased by 60%")
        finally:
            cursor.close()
            self.db.close()

    def buy_fuel(self, fuel_amount):
        conn = self.db.connect()
        if not conn:
            print("Database connection failed.")
            return

        cursor = conn.cursor()
        try:
            cost = fuel_amount * 5
            cursor.execute("SELECT total_money FROM player WHERE player_id = %s", (self.player_id,))
            money = cursor.fetchone()[0]

            if money >= cost:
                cursor.execute(
                    """
                    UPDATE player 
                    SET total_money = total_money - %s, fuel_amount = fuel_amount + %s 
                    WHERE player_id = %s
                    """,
                    (cost, fuel_amount, self.player_id)
                )
                conn.commit()
                print(f"Bought {fuel_amount} fuel units for {cost} money.")
            else:
                print("Not enough money to buy fuel.")
        finally:
            cursor.close()
            self.db.close()

    def main_menu(self):
        self.start_game()
        self.set_unfavorable_weather()

        while True:
            print("\nOptions:")
            print("1 - Fly to next airport")
            print("2 - Buy fuel")
            print("3 - Exit game")
            choice = int(input("Enter your choice: "))

            if choice == 1:
                self.get_airports_with_distances()
            elif choice == 2:
                fuel_amount = int(input("Enter the amount of fuel to buy: "))
                self.buy_fuel(fuel_amount)
            elif choice == 3:
                print("Exiting game. Thank you for playing!")
                break
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    game = Game()
    game.main_menu()
