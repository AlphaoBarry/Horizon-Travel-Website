from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from your_database_module import get_customer_details  # Import your database function

app = Flask(__name__)

@app.route('/customer_details')
def customer_details():
    customer = get_customer_details()  # Fetch customer details from the database
    return render_template('CustomerDetails.html', customer=customer)

@app.route('/book_trip', methods=['POST'])
def book_trip():
    customer_id = 1  # Replace with actual customer ID from session or other source
    departure_date = request.form['departure_date']  # Use Date instead of FlightID
    seats = request.form['num_seats']
    status = request.form['class_type']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Bookings_HT (CustomerID, Date, Seats, Status)
        VALUES (?, ?, ?, ?)
    ''', (customer_id, departure_date, seats, status))
    conn.commit()
    conn.close()

    return redirect(url_for('booking_confirmation'))

@app.route('/booking_confirmation')
def booking_confirmation():
    return "Booking confirmed!"

@app.route('/routes_ht')
def routes_ht():
    conn = sqlite3.connect('your_database.db')  # Replace with your database path
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Routes_HT")
    routes = cursor.fetchall()
    conn.close()
    return render_template('routes_ht.html', routes=routes)

if __name__ == '__main__':
    app.run(debug=True)
