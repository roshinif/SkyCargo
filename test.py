import random
import mysql.connector
from math import radians, sin, cos, sqrt, atan2

def connect_to_db():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='12345',
            database='flight_path',
            autocommit=True
        )
        if conn.is_connected():
            print("Connection Established")
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

#Start Game
def start_game():
    conn = connect_to_db()
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
        player_id = int(cursor.fetchone()[0])
        print(f"Player created with ID: {player_id}")
        return player_id
    finally:
        cursor.close()
        conn.close()

# Calculate Distance
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def get_airports_with_distances(player_id):
    conn = connect_to_db()
    if not conn:
        print("Database connection failed.")
        return

    cursor = conn.cursor(dictionary=True)  # Use dictionary=True for easier access to column names
    try:
        # Get the end_location and its coordinates for the player
        cursor.execute("""
            SELECT end_location, latitude_deg, longitude_deg
            FROM player
            JOIN new_airports ON player.end_location = new_airports.airport_code
            WHERE player.player_id = %s
        """, (player_id,))
        player_location = cursor.fetchone()

        if not player_location:
            print(f"No location data found for player_id {player_id}.")
            return

        end_location = player_location["end_location"]
        end_lat = float(player_location["latitude_deg"])
        end_lon = float(player_location["longitude_deg"])

        # Get all airports with their codes and coordinates
        cursor.execute("""
            SELECT airport_code, airport_name, latitude_deg, longitude_deg
            FROM new_airports
        """)
        airports = cursor.fetchall()

        # Calculate distances and display the results
        print(f"Distances from {end_location} to other airports:")
        airport_distances = []
        for airport in airports:
            airport_code = airport["airport_code"]
            airport_name = airport["airport_name"]
            lat = float(airport["latitude_deg"])
            lon = float(airport["longitude_deg"])
            distance = calculate_distance(end_lat, end_lon, lat, lon)
            airport_distances.append((airport_code, airport_name, distance))

        # Sort by distance
        airport_distances.sort(key=lambda x: x[2])

        # Print sorted distances
        for code, name, dist in airport_distances:
            print(f"{code}: {dist:.2f} km")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

def set_unfavorable_weather():

    conn = connect_to_db()
    if conn is None:
        print("Failed to connect to database.")
        return

    cursor = conn.cursor()

    cursor.execute("SELECT airport_code FROM new_airports")
    airport_codes = [row[0] for row in cursor.fetchall()]

    print("Number of Airports:", len(airport_codes))

    # Randomly select 3 airport IDs
    unfavorable_airports = random.sample(airport_codes, 3)

    # Update the selected airports with high consumption
    cursor.executemany(
        "UPDATE new_airports SET high_consumption = 1 WHERE airport_code = %s",
        [(airport_code,) for airport_code in unfavorable_airports]
    )
    conn.commit()

    # Display the airports with unfavorable weather
    cursor.execute(
        "SELECT airport_code, airport_name FROM new_airports WHERE high_consumption = 1"
    )
    print("Airports with unfavorable weather:")
    for airport in cursor.fetchall():
        print(f" - {airport[0]} ({airport[1]}) - Fuel consumption increased by 60%")

    # Close the connection
    cursor.close()
    conn.close()

def get_fuel_consumption(player_id, airport_code):

    conn = connect_to_db()
    if conn is None:
        print("Failed to connect to database.")
        return None

    cursor = conn.cursor()

    # Check if the airport has high consumption due to unfavorable weather
    cursor.execute(
        "SELECT high_consumption FROM new_airports WHERE airport_code = %s",
        (airport_code,)
    )
    result = cursor.fetchone()
    if result and result[0] == 1:
        print("Unfavorable weather detected. Fuel consumption increased by 60%.")
        return 1.6  # 60% increase in fuel consumption
    else:
        return 1.0  # Normal fuel consumption


# Fly to Airport
def fly_to_airport(player_id, target_airport):
    conn = connect_to_db()
    if not conn:
        print("Database connection failed.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT latitude_deg, longitude_deg FROM new_airports WHERE airport_code = %s", (target_airport,))
        target_coords = cursor.fetchone()

        cursor.execute(
            """
            SELECT latitude_deg, longitude_deg FROM new_airports 
            WHERE airport_code = (SELECT end_location FROM player WHERE player_id = %s)
            """,
            (player_id,)
        )
        current_coords = cursor.fetchone()

        if target_coords and current_coords:
            distance = calculate_distance(current_coords[0], current_coords[1], target_coords[0], target_coords[1])
            multiplier = get_fuel_consumption(player_id, target_airport)
            fuel_needed = int(0.5 * distance)  # 2 fuel units per km

            cursor.execute("SELECT fuel_amount, total_money FROM player WHERE player_id = %s", (player_id,))
            player_stats = cursor.fetchone()

            if player_stats[0] < fuel_needed:
                print("Not enough fuel. Buy fuel or choose another airport.")
            else:
                cursor.execute(
                    """
                    UPDATE player 
                    SET fuel_amount = fuel_amount - %s, end_location = %s 
                    WHERE player_id = %s
                    """,
                    (fuel_needed, target_airport, player_id)
                )
                conn.commit()
                fuel_left = player_stats[0] - fuel_needed
                distance_can_travel = fuel_left*2
                print(f"Traveled to {target_airport}. Fuel left: {fuel_left}. Reachable Distance: {distance_can_travel:.2f} km")

        else:
            print("Invalid airport code.")
    finally:
        cursor.close()
        conn.close()

# Buy Fuel
def buy_fuel(player_id, fuel_amount):
    conn = connect_to_db()
    if not conn:
        print("Database connection failed.")
        return

    cursor = conn.cursor()
    try:
        cost = fuel_amount * 5  # 5 money units per 1 fuel unit
        cursor.execute("SELECT total_money FROM player WHERE player_id = %s", (player_id,))
        money = cursor.fetchone()[0]

        if money >= cost:
            cursor.execute(
                """
                UPDATE player 
                SET total_money = total_money - %s, fuel_amount = fuel_amount + %s 
                WHERE player_id = %s
                """,
                (cost, fuel_amount, player_id)
            )
            conn.commit()
            print(f"Bought {fuel_amount} fuel units for {cost} money.")
        else:
            print("Not enough money to buy fuel.")
    finally:
        cursor.close()
        conn.close()

# Collect Cargo
def collect_cargo(player_id):
    conn = connect_to_db()
    if not conn:
        print("Database connection failed.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT end_location FROM player WHERE player_id = %s", (player_id,))
        result = cursor.fetchone()
        if not result:
            print(f"No end_location found for player_id {player_id}")
            return

        current_location = result[0]
        query = """
                SELECT goal.value 
                FROM goal 
                JOIN new_airports ON goal.goal_id = new_airports.goal_type 
                WHERE new_airports.airport_code = %s
                """
        cursor.execute(query, (current_location,))
        result = cursor.fetchone()
        if not result:
            print("No cargo available at this airport.")
            return

        cargo_value = result[0]
        cursor.execute(
            """
            UPDATE player 
            SET total_money = total_money + %s, cargo_collected = cargo_collected + 1 
            WHERE player_id = %s
            """,
            (cargo_value, player_id)
        )
        conn.commit()
        print(f"Collected cargo worth {cargo_value} money.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

# Check Status
def check_status(player_id):
    conn = connect_to_db()
    if not conn:
        print("Database connection failed.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM player WHERE player_id = %s", (player_id,))
        status = cursor.fetchone()
        if status:
            print("Player Status:")
            print(f"Name: {status[1]}")
            print(f"Fuel: {status[7]}")
            print(f"Money: {status[5]}")
            print(f"Cargo Collected: {status[6]}")
            print(f"Current Location: {status[3]}")
        else:
            print(f"No player found with ID {player_id}.")
    finally:
        cursor.close()
        conn.close()



# Main program
def main():
    player_id = start_game()
    if not player_id:
        return

    set_unfavorable_weather()

    while True:
        print("\nOptions:")
        print("1 - Fly to next airport")
        print("2 - Buy fuel")
        print("3 - Collect cargo")
        print("4 - Check status")
        print("5 - Exit game")
        choice = int(input("Enter your choice: "))

        if choice == 1:
            get_airports_with_distances(player_id)
            target_airport = input("Enter the airport code: ")
            fly_to_airport(player_id, target_airport)

        elif choice == 2:
            fuel_amount = int(input("Enter the amount of fuel to buy: "))
            buy_fuel(player_id, fuel_amount)
        elif choice == 3:
            collect_cargo(player_id)
        elif choice == 4:
            check_status(player_id)
        elif choice == 5:
            print("Exiting game. Thank you for playing!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
