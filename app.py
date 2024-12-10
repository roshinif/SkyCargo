from flask import Flask, request, render_template, redirect
import random
from db_connection import Database
import mysql.connector
from math import radians, sin, cos, sqrt, atan2

from mysql.connector import cursor

app = Flask(__name__)

db = Database(host="localhost", user="root", password="12345", database="flight_path")
db.connect()
cursor=db.cursor(dictionary=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/game')
def game():
    player_id = request.args.get('player_id')
    if not player_id:
        return redirect('/')

    query = "SELECT * FROM player WHERE player_id = %s"
    cursor.execute(query, (player_id,))
    player = cursor.fetchone()

    if not player:
        return redirect('/')

    return render_template('game.html', player=player)

@app.route('/game/<player_name>')
def start_game(player_name=None):
    cursor=db.cursor()
    if not db:
        return "Database connection failed."
        

    cursor = db.cursor()
    try:
        cursor.execute("""UPDATE new_airports SET high_consumption=0;""")
        db.commit()
        
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
        db.commit()
        cursor.execute("SELECT LAST_INSERT_ID()")
        player_id = cursor.fetchone()[0]
        response = {"playerID": player_id}
        return response

    finally:
        cursor.close()
        db.close()

if __name__ == '__main__':
    app.run(use_reloader=True, host='127.0.0.1', port=5000)
