from flask import Flask, render_template, request, redirect, url_for, flash, session
import DBfunc
import qrcode
import os
import random  # Add this import for generating random FlightID
import bcrypt # Add this import for password hashing

from flask_mail import Mail, Message
from datetime import datetime


app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for session management and flash messages

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your email provider's SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '*********@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = '*******%'  # Replace with your email password
app.config['MAIL_DEFAULT_SENDER'] = 'abarry706@gmail.com'
mail = Mail(app)

# Database Connection
db = DBfunc.getConnection()
cursor = db.cursor()



# Ensure the table schema is correct
DBfunc.ensureTableSchema()



# Home Page
@app.route('/')
def home():
    return render_template('website1.html')



# Sign-up Page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')  # Safely get form data
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Check if fields are empty
        if not name or not email or not password or not confirm_password:
            flash("All fields are required!", "danger")
            return redirect(url_for('signup'))

        # Check if passwords match
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('signup'))

        # Check if email is already registered
        cursor.execute("SELECT * FROM Customers_HT2 WHERE Email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Email already registered!", "danger")
            return redirect(url_for('signup'))

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Insert new user into database
        cursor.execute("INSERT INTO Customers_HT2 (Name, Email, Password) VALUES (%s, %s, %s)", 
                       (name, email, hashed_password.decode('utf-8')))
        db.commit()

        flash("Sign-up successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('SignInPage.html')



# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')  # Safely get form data
        password = request.form.get('password')

        # Check if fields are empty
        if not email or not password:
            flash("Email and password are required!", "danger")
            return redirect(url_for('login'))

        # Verify if the user exists with the given email
        cursor.execute("SELECT * FROM Customers_HT2 WHERE Email = %s", (email,))
        user = cursor.fetchone()

        if user:
            # Compare the hashed password
            stored_password = user[3]  # Assuming the password is stored in the 4th column
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                session['CustomerID'] = user[0]  # Store CustomerID in session
                flash("Login successful!", "success")
                return redirect(url_for('booking'))  # Redirect to destination page after successful login
            else:
                flash("Invalid email or password!", "danger")
        else:
            flash("Invalid email or password!", "danger")

        return redirect(url_for('login'))

    return render_template('LoginPage.html')



# Logout Page
@app.route('/logout')
def logout():
    session.pop('CustomerID', None)  # Clear the CustomerID from the session
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))




# Customer details page
@app.route('/CustomerInfo')
def CustomerInfo():
    customer_id = session.get('CustomerID')
    if not customer_id:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))

    # Fetch customer details
    cursor.execute("SELECT Name, Email, CustomerID FROM Customers_HT2 WHERE CustomerID = %s", (customer_id,))
    customer = cursor.fetchone()

    # Fetch booking details with destination, total price, discounted price, and discount percentage
    cursor.execute("""
        SELECT b.BookingID, b.Route, f.Destination, b.Seats, b.Status, b.Date, f.Price,
               CASE
                   WHEN b.Status = 'Business' THEN (b.Seats * f.Price * 2)
                   ELSE (b.Seats * f.Price)
               END AS TotalPrice,
               b.Spendings AS TotalPriceAfterDiscount,
               CASE
                   WHEN (CASE
                             WHEN b.Status = 'Business' THEN (b.Seats * f.Price * 2)
                             ELSE (b.Seats * f.Price)
                         END) > 0
                   THEN ROUND(((CASE
                                   WHEN b.Status = 'Business' THEN (b.Seats * f.Price * 2)
                                   ELSE (b.Seats * f.Price)
                               END) - b.Spendings) / 
                               (CASE
                                   WHEN b.Status = 'Business' THEN (b.Seats * f.Price * 2)
                                   ELSE (b.Seats * f.Price)
                               END) * 100, 2)
                   ELSE 0
               END AS DiscountPercentage
        FROM Bookings_HT b
        JOIN Flights_HT f ON b.Route = f.FlightID
        WHERE b.CustomerID = %s
    """, (customer_id,))
    bookings = cursor.fetchall()

    if customer:
        customer_details = {
            'name': customer[0],
            'email': customer[1],
            'CustomerID': customer[2]
        }
        return render_template('CustomerDetails.html', customer=customer_details, bookings=bookings)
    else:
        flash("Customer details not found!", "danger")
        return redirect(url_for('home'))



# Update customer details
@app.route('/update_password', methods=['GET', 'POST'])
def update_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        customer_id = session.get('CustomerID')
        if not customer_id:
            flash("You need to log in first!", "danger")
            return redirect(url_for('login'))

        cursor.execute("SELECT Password FROM Customers_HT2 WHERE CustomerID = %s", (customer_id,))
        customer = cursor.fetchone()

        if customer and bcrypt.checkpw(current_password.encode('utf-8'), customer[0].encode('utf-8')):
            if new_password == confirm_password:
                hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                cursor.execute("UPDATE Customers_HT2 SET Password = %s WHERE CustomerID = %s", 
                               (hashed_new_password.decode('utf-8'), customer_id))
                db.commit()
                flash("Password updated successfully!", "success")
                return redirect(url_for('CustomerInfo'))
            else:
                flash("New passwords do not match!", "danger")
        else:
            flash("Current password is incorrect!", "danger")

    return render_template('UpdatePassword.html')



# Booking page
@app.route('/booking')
def booking():
    customer_id = session.get('CustomerID')  # Ensure the user is logged in
    if not customer_id:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))

    # Check if the user is an admin
    cursor.execute("SELECT is_admin FROM Customers_HT2 WHERE CustomerID = %s", (customer_id,))
    user = cursor.fetchone()
    is_admin = user[0] if user else False

    # Query the Flights_HT table to retrieve FlightID, Destination, Date, and Price
    cursor.execute("SELECT FlightID, Destination, Date, Price FROM Flights_HT")
    flights = [
        {
            "FlightID": row[0],
            "Destination": row[1],
            "Date": row[2],
            "Price": row[3],
        }
        for row in cursor.fetchall()
    ]

    # Pass the flights data and is_admin to the template
    return render_template('BookingPage.html', flights=flights, is_admin=is_admin)

# Booking page
@app.route('/book_trip', methods=['POST'])
def book_trip():
    customer_id = session.get('CustomerID')  # Retrieve CustomerID from session
    if not customer_id:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))

    # Retrieve form data
    departure_date = request.form.get('departure_date')
    route = request.form.get('route')
    num_seats = request.form.get('num_seats')
    class_type = request.form.get('class_type')  # Updated to match the new constraint

    # Validate form data
    if not departure_date or not route or not num_seats or not class_type:
        flash("All fields are required!", "danger")
        return redirect(url_for('booking'))

    # Ensure class_type is either "Business" or "Economy"
    if class_type not in ["Business", "Economy"]:
        flash("Invalid class type selected!", "danger")
        return redirect(url_for('booking'))

    try:
        # Ensure num_seats is an integer
        num_seats = int(num_seats)

        # Fetch the base price for the selected route
        cursor.execute("SELECT Price, AirlineID FROM Flights_HT WHERE FlightID = %s", (route,))
        flight = cursor.fetchone()
        if not flight:
            flash("Invalid route selected!", "danger")
            return redirect(url_for('booking'))

        base_price = flight[0]
        airline_id = flight[1]

        # Adjust the price based on the class type
        if class_type == "Business":
            total_price = base_price * 2 * num_seats  # Double the price for Business
        else:
            total_price = base_price * num_seats  # Normal price for Economy

        # Calculate the number of days between the booking date and the departure date
        booking_date = datetime.now().date()  # Current date when the booking is made
        departure_date_obj = datetime.strptime(departure_date, "%Y-%m-%d").date()  # Convert departure date to a date object
        days_difference = (departure_date_obj - booking_date).days  # Difference in days

        # Debugging: Print the days difference
        print(f"Booking Date: {booking_date}, Departure Date: {departure_date_obj}, Days Difference: {days_difference}")

        # Apply discount based on the number of days
        discount_percentage = 0
        if 80 <= days_difference <= 90:
            discount_percentage = 25
        elif 60 <= days_difference <= 79:
            discount_percentage = 15
        elif 45 <= days_difference <= 59:
            discount_percentage = 10

        discount_amount = (total_price * discount_percentage) / 100
        total_price -= discount_amount  # Apply the discount

        # Debugging: Print the discount percentage and total price after discount
        print(f"Discount Percentage: {discount_percentage}%, Discount Amount: {discount_amount}, Total Price: {total_price}")

        # Check seat availability in the Airlines_HT table
        if class_type == "Business":
            cursor.execute("SELECT BusinessSeats FROM Airlines_HT WHERE AirlineID = %s", (airline_id,))
            available_seats = cursor.fetchone()[0]
            if available_seats < num_seats:
                flash("Not enough Business seats available!", "danger")
                return redirect(url_for('booking'))

            # Decrement the number of Business seats
            cursor.execute("""
                UPDATE Airlines_HT
                SET BusinessSeats = BusinessSeats - %s
                WHERE AirlineID = %s
            """, (num_seats, airline_id))
        else:
            cursor.execute("SELECT EcoSeats FROM Airlines_HT WHERE AirlineID = %s", (airline_id,))
            available_seats = cursor.fetchone()[0]
            if available_seats < num_seats:
                flash("Not enough Economy seats available!", "danger")
                return redirect(url_for('booking'))

            # Decrement the number of Economy seats
            cursor.execute("""
                UPDATE Airlines_HT
                SET EcoSeats = EcoSeats - %s
                WHERE AirlineID = %s
            """, (num_seats, airline_id))

        # Insert booking information into the Bookings_HT table, including Spendings
        cursor.execute("""
            INSERT INTO Bookings_HT (CustomerID, Date, Route, Seats, Status, Spendings)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (customer_id, departure_date, route, num_seats, class_type, total_price))
        
        # Get the BookingID of the newly created booking
        booking_id = cursor.lastrowid

        # Generate a QR code for the booking
        qr_data = f"Booking ID: {booking_id}\nCustomer ID: {customer_id}\nRoute: {route}\nDeparture Date: {departure_date}\nSeats: {num_seats}\nClass: {class_type}\nTotal Price: ${total_price:.2f}"
        qr = qrcode.make(qr_data)
        qr_image_path = os.path.join('static', f'qr_{booking_id}.png')
        qr.save(qr_image_path)

        # Commit the transaction
        db.commit()

        flash(f"Trip booked successfully for Date: {departure_date}! Total Price after {discount_percentage}% discount: ${total_price:.2f}", "success")
        return redirect(url_for('booking'))

    except ValueError as ve:
        print(f"ValueError: {ve}")
        flash("Number of seats must be a valid integer!", "danger")
        return redirect(url_for('booking'))

    except Exception as e:
        print(f"Database error: {e}")
        flash(f"An error occurred while saving the booking: {e}", "danger")
        return redirect(url_for('booking'))


#update booking
@app.route('/update_booking/<int:booking_id>', methods=['GET', 'POST'])
def update_booking(booking_id):
    customer_id = session.get('CustomerID')  # Ensure the user is logged in
    if not customer_id:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Retrieve updated booking details from the form
        new_departure_date = request.form.get('departure_date')
        new_num_seats = request.form.get('num_seats')
        new_class_type = request.form.get('class_type')

        # Validate the form data
        if not new_departure_date or not new_num_seats or not new_class_type:
            flash("All fields are required!", "danger")
            return redirect(url_for('update_booking', booking_id=booking_id))

        try:
            # Ensure num_seats is an integer
            new_num_seats = int(new_num_seats)

            # Fetch the base price for the route
            cursor.execute("""
                SELECT f.Price
                FROM Bookings_HT b
                JOIN Flights_HT f ON b.Route = f.FlightID
                WHERE b.BookingID = %s AND b.CustomerID = %s
            """, (booking_id, customer_id))
            flight = cursor.fetchone()

            if not flight:
                flash("Invalid booking or route!", "danger")
                return redirect(url_for('update_booking', booking_id=booking_id))

            base_price = flight[0]

            # Calculate the total price based on the class type
            if new_class_type == "Business":
                total_price = base_price * 2 * new_num_seats  # Double the price for Business
            else:
                total_price = base_price * new_num_seats  # Normal price for Economy

            # Calculate the number of days between the booking date and the departure date
            booking_date = datetime.now().date()  # Current date when the update is made
            departure_date_obj = datetime.strptime(new_departure_date, "%Y-%m-%d").date()  # Convert departure date to a date object
            days_difference = (departure_date_obj - booking_date).days  # Difference in days

            # Apply discount based on the number of days
            discount_percentage = 0
            if 80 <= days_difference <= 90:
                discount_percentage = 25
            elif 60 <= days_difference <= 79:
                discount_percentage = 15
            elif 45 <= days_difference <= 59:
                discount_percentage = 10

            discount_amount = (total_price * discount_percentage) / 100
            total_price -= discount_amount  # Apply the discount

            # Debugging: Print the discount percentage and total price after discount
            print(f"Discount Percentage: {discount_percentage}%, Discount Amount: {discount_amount}, Total Price: {total_price}")

            # Update the booking in the database
            cursor.execute("""
                UPDATE Bookings_HT
                SET Date = %s, Seats = %s, Status = %s, Spendings = %s
                WHERE BookingID = %s AND CustomerID = %s
            """, (new_departure_date, new_num_seats, new_class_type, total_price, booking_id, customer_id))
            db.commit()

            flash("Booking updated successfully!", "success")
            return redirect(url_for('CustomerInfo'))

        except Exception as e:
            print(f"Error updating booking: {e}")
            flash("An error occurred while updating the booking.", "danger")
            return redirect(url_for('update_booking', booking_id=booking_id))

    # Fetch the current booking details to pre-fill the form
    cursor.execute("""
        SELECT Date, Seats, Status
        FROM Bookings_HT
        WHERE BookingID = %s AND CustomerID = %s
    """, (booking_id, customer_id))
    booking = cursor.fetchone()

    if not booking:
        flash("Booking not found or unauthorized access!", "danger")
        return redirect(url_for('CustomerInfo'))

    # Pass booking details and booking_id to the template
    return render_template('UpdateBooking.html', booking=booking, booking_id=booking_id)

    # Fetch the current booking details to pre-fill the form
    cursor.execute("""
        SELECT Date, Seats, Status
        FROM Bookings_HT
        WHERE BookingID = %s AND CustomerID = %s
    """, (booking_id, customer_id))
    booking = cursor.fetchone()

    if not booking:
        flash("Booking not found or unauthorized access!", "danger")
        return redirect(url_for('CustomerInfo'))

    # Pass booking details and booking_id to the template
    return render_template('UpdateBooking.html', booking=booking, booking_id=booking_id)



#cancel booking
@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    customer_id = session.get('CustomerID')  # Ensure the user is logged in
    if not customer_id:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))

    booking_id = request.form.get('booking_id')  # Get the booking ID from the form
    if not booking_id:
        flash("Invalid booking ID!", "danger")
        return redirect(url_for('CustomerInfo'))

    try:
        # Fetch the booking details to determine the number of seats and class type
        cursor.execute("""
            SELECT b.Seats, b.Status, f.AirlineID
            FROM Bookings_HT b
            JOIN Flights_HT f ON b.Route = f.FlightID
            WHERE b.BookingID = %s AND b.CustomerID = %s
        """, (booking_id, customer_id))
        booking = cursor.fetchone()

        if not booking:
            flash("Booking not found or unauthorized access!", "danger")
            return redirect(url_for('CustomerInfo'))

        num_seats = booking[0]
        class_type = booking[1]
        airline_id = booking[2]

        # Add the seats back to the Airlines_HT table based on the class type
        if class_type == "Business":
            cursor.execute("""
                UPDATE Airlines_HT
                SET BusinessSeats = BusinessSeats + %s
                WHERE AirlineID = %s
            """, (num_seats, airline_id))
        else:
            cursor.execute("""
                UPDATE Airlines_HT
                SET EcoSeats = EcoSeats + %s
                WHERE AirlineID = %s
            """, (num_seats, airline_id))

        # Delete the booking from the database
        cursor.execute("DELETE FROM Bookings_HT WHERE BookingID = %s AND CustomerID = %s", (booking_id, customer_id))
        db.commit()

        flash("Booking canceled successfully, and seats have been added back!", "success")
    except Exception as e:
        print(f"Error canceling booking: {e}")
        flash("An error occurred while canceling the booking.", "danger")

    return redirect(url_for('CustomerInfo'))


# Error handling
@app.route('/about')
def about():
    return render_template('AboutPage.html')



# Error handling
@app.route('/destination')
def destination():
    return render_template('DestinationInfoPage.html')



# Error handling
@app.route('/401')
def un_autorized(error):
    return render_template('401.html'), 401



@app.route('/routes_ht')
def routes_ht():
    cursor.execute("SELECT RouteID, Route FROM Routes_HT")
    routes = cursor.fetchall()
    return render_template('routes_ht.html', routes=routes)

#qr code
@app.route('/view_qr_code/<int:booking_id>', methods=['GET'])
def view_qr_code(booking_id):
    customer_id = session.get('CustomerID')  # Ensure the user is logged in
    if not customer_id:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))

    # Check if the booking exists and belongs to the logged-in customer
    cursor.execute("SELECT BookingID FROM Bookings_HT WHERE BookingID = %s AND CustomerID = %s", (booking_id, customer_id))
    booking = cursor.fetchone()

    if not booking:
        flash("Booking not found or unauthorized access!", "danger")
        return redirect(url_for('CustomerInfo'))

    # Generate the QR code file path
    qr_image_path = url_for('static', filename=f'qr_{booking_id}.png')

    return render_template('ViewQRCode.html', qr_image_path=qr_image_path)


#admin page
@app.route('/admin/flights', methods=['GET', 'POST'])
def admin_flights():
    customer_id = session.get('CustomerID')  # Ensure the user is logged in
    if not customer_id:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))

    # Check if the user is an admin
    cursor.execute("SELECT is_admin FROM Customers_HT2 WHERE CustomerID = %s", (customer_id,))
    user = cursor.fetchone()
    if not user or not user[0]:
        flash("Unauthorized access! Admins only.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Handle form submission to update the Flights_HT table
        flight_id = request.form.get('flight_id')
        destination = request.form.get('destination')
        date = request.form.get('date')
        price = request.form.get('price')

        if not flight_id or not destination or not date or not price:
            flash("All fields are required!", "danger")
            return redirect(url_for('admin_flights'))

        try:
            # Update the Flights_HT table
            cursor.execute("""
                UPDATE Flights_HT
                SET Destination = %s, Date = %s, Price = %s
                WHERE FlightID = %s
            """, (destination, date, price, flight_id))
            db.commit()
            flash("Flight updated successfully!", "success")
        except Exception as e:
            print(f"Error updating flight: {e}")
            flash("An error occurred while updating the flight.", "danger")

    # Fetch all flights to display in the admin panel
    cursor.execute("SELECT FlightID, Destination, Date, Price FROM Flights_HT")
    flights = cursor.fetchall()

    return render_template('AdminFlights.html', flights=flights)

@app.route('/add_flight', methods=['POST'])
def add_flight():
    customer_id = session.get('CustomerID')  # Ensure the user is logged in
    if not customer_id:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))

    # Check if the user is an admin
    cursor.execute("SELECT is_admin FROM Customers_HT2 WHERE CustomerID = %s", (customer_id,))
    user = cursor.fetchone()
    if not user or not user[0]:
        flash("Unauthorized access! Admins only.", "danger")
        return redirect(url_for('home'))

    # Retrieve form data
    flight_id = request.form.get('flight_id')
    destination = request.form.get('destination')
    date = request.form.get('date')
    price = request.form.get('price')

    if not flight_id or not destination or not date or not price:
        flash("All fields are required!", "danger")
        return redirect(url_for('admin_flights'))

    try:
        # Insert new flight into the Flights_HT table
        cursor.execute("""
            INSERT INTO Flights_HT (FlightID, Destination, Date, Price)
            VALUES (%s, %s, %s, %s)
        """, (flight_id, destination, date, price))
        db.commit()
        flash("New flight added successfully!", "success")
    except Exception as e:
        print(f"Error adding flight: {e}")
        flash("An error occurred while adding the flight.", "danger")

    return redirect(url_for('admin_flights'))


@app.route('/delete_flight', methods=['POST'])
def delete_flight():
    customer_id = session.get('CustomerID')  # Ensure the user is logged in
    if not customer_id:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))

    # Check if the user is an admin
    cursor.execute("SELECT is_admin FROM Customers_HT2 WHERE CustomerID = %s", (customer_id,))
    user = cursor.fetchone()
    if not user or not user[0]:
        flash("Unauthorized access! Admins only.", "danger")
        return redirect(url_for('home'))

    # Retrieve flight ID from the form
    flight_id = request.form.get('flight_id')

    if not flight_id:
        flash("Invalid flight ID!", "danger")
        return redirect(url_for('admin_flights'))

    try:
        # Delete the flight from the Flights_HT table
        cursor.execute("DELETE FROM Flights_HT WHERE FlightID = %s", (flight_id,))
        db.commit()
        flash("Flight deleted successfully!", "success")
    except Exception as e:
        print(f"Error deleting flight: {e}")
        flash("An error occurred while deleting the flight.", "danger")

    return redirect(url_for('admin_flights'))


#Admin/Customer page
# Admin/Customer page
@app.route('/admin/customers', methods=['GET', 'POST'])
def admin_customers():
    customer_id = session.get('CustomerID')  # Ensure the user is logged in
    if not customer_id:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))

    # Check if the user is an admin
    cursor.execute("SELECT is_admin FROM Customers_HT2 WHERE CustomerID = %s", (customer_id,))
    user = cursor.fetchone()
    if not user or not user[0]:
        flash("Unauthorized access! Admins only.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Handle adding, editing, or deleting customers
        action = request.form.get('action')

        if action == 'add':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')

            if not name or not email or not password:
                flash("All fields are required to add a customer!", "danger")
                return redirect(url_for('admin_customers'))

            try:
                # Hash the password
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

                # Insert the new customer into the database
                cursor.execute("""
                    INSERT INTO Customers_HT2 (Name, Email, Password)
                    VALUES (%s, %s, %s)
                """, (name, email, hashed_password.decode('utf-8')))
                db.commit()
                flash("Customer added successfully!", "success")
            except Exception as e:
                print(f"Error adding customer: {e}")
                flash("An error occurred while adding the customer.", "danger")

        elif action == 'edit':
            customer_id = request.form.get('customer_id')
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')  # Optional: Only hash if provided

            if not customer_id or not name or not email:
                flash("All fields are required to edit a customer!", "danger")
                return redirect(url_for('admin_customers'))

            try:
                if password:  # If a new password is provided, hash it
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    cursor.execute("""
                        UPDATE Customers_HT2
                        SET Name = %s, Email = %s, Password = %s
                        WHERE CustomerID = %s
                    """, (name, email, hashed_password.decode('utf-8'), customer_id))
                else:  # If no password is provided, update only the name and email
                    cursor.execute("""
                        UPDATE Customers_HT2
                        SET Name = %s, Email = %s
                        WHERE CustomerID = %s
                    """, (name, email, customer_id))
                db.commit()
                flash("Customer updated successfully!", "success")
            except Exception as e:
                print(f"Error updating customer: {e}")
                flash("An error occurred while updating the customer.", "danger")

        elif action == 'delete':
            customer_id = request.form.get('customer_id')

            if not customer_id:
                flash("Customer ID is required to delete a customer!", "danger")
                return redirect(url_for('admin_customers'))

            try:
                cursor.execute("DELETE FROM Customers_HT2 WHERE CustomerID = %s", (customer_id,))
                db.commit()
                flash("Customer deleted successfully!", "success")
            except Exception as e:
                print(f"Error deleting customer: {e}")
                flash("An error occurred while deleting the customer.", "danger")

    # Fetch all customers to display in the admin panel
    cursor.execute("SELECT CustomerID, Name, Email FROM Customers_HT2")
    customers = cursor.fetchall()

    return render_template('AdminCustomers.html', customers=customers)



#admin booking page
@app.route('/admin/bookings', methods=['GET', 'POST'])
def admin_bookings():
    customer_id = session.get('CustomerID')  # Ensure the user is logged in
    if not customer_id:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))

    # Check if the user is an admin
    cursor.execute("SELECT is_admin FROM Customers_HT2 WHERE CustomerID = %s", (customer_id,))
    user = cursor.fetchone()
    if not user or not user[0]:
        flash("Unauthorized access! Admins only.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Handle modifying or deleting bookings
        action = request.form.get('action')
        if action == 'edit':
            booking_id = request.form.get('booking_id')
            new_date = request.form.get('date')
            new_seats = request.form.get('seats')
            new_status = request.form.get('status')

            if not booking_id or not new_date or not new_seats or not new_status:
                flash("All fields are required to edit a booking!", "danger")
                return redirect(url_for('admin_bookings'))

            try:
                # Ensure new_seats is an integer
                new_seats = int(new_seats)

                # Fetch the route and base price for the booking
                cursor.execute("""
                    SELECT Route
                    FROM Bookings_HT
                    WHERE BookingID = %s
                """, (booking_id,))
                booking = cursor.fetchone()

                if not booking:
                    flash("Booking not found!", "danger")
                    return redirect(url_for('admin_bookings'))

                route = booking[0]

                # Fetch the base price for the route
                cursor.execute("SELECT Price FROM Flights_HT WHERE FlightID = %s", (route,))
                flight = cursor.fetchone()
                if not flight:
                    flash("Invalid route for the booking!", "danger")
                    return redirect(url_for('admin_bookings'))

                base_price = flight[0]

                # Recalculate the total price based on the new details
                if new_status == "Business":
                    total_price = base_price * 2 * new_seats  # Double the price for Business
                else:
                    total_price = base_price * new_seats  # Normal price for Economy

                # Calculate the number of days between the current date and the new departure date
                booking_date = datetime.now().date()  # Current date
                departure_date_obj = datetime.strptime(new_date, "%Y-%m-%d").date()  # Convert new date to a date object
                days_difference = (departure_date_obj - booking_date).days  # Difference in days

                # Apply discount based on the number of days
                discount_percentage = 0
                if 80 <= days_difference <= 90:
                    discount_percentage = 25
                elif 60 <= days_difference <= 79:
                    discount_percentage = 15
                elif 45 <= days_difference <= 59:
                    discount_percentage = 10

                discount_amount = (total_price * discount_percentage) / 100
                total_price -= discount_amount  # Apply the discount

                # Debugging: Print the discount percentage and total price after discount
                print(f"Discount Percentage: {discount_percentage}%, Discount Amount: {discount_amount}, Total Price: {total_price}")

                # Update the booking in the database
                cursor.execute("""
                    UPDATE Bookings_HT
                    SET Date = %s, Seats = %s, Status = %s, Spendings = %s
                    WHERE BookingID = %s
                """, (new_date, new_seats, new_status, total_price, booking_id))
                db.commit()

                flash("Booking updated successfully!", "success")
            except Exception as e:
                print(f"Error updating booking: {e}")
                flash("An error occurred while updating the booking.", "danger")

        elif action == 'delete':
            booking_id = request.form.get('booking_id')

            if not booking_id:
                flash("Booking ID is required to delete a booking!", "danger")
                return redirect(url_for('admin_bookings'))

            try:
                cursor.execute("DELETE FROM Bookings_HT WHERE BookingID = %s", (booking_id,))
                db.commit()
                flash("Booking deleted successfully!", "success")
            except Exception as e:
                print(f"Error deleting booking: {e}")
                flash("An error occurred while deleting the booking.", "danger")

    # Fetch all bookings to display in the admin panel
    cursor.execute("""
        SELECT b.BookingID, c.Name, c.Email, b.Route, b.Seats, b.Status, b.Date, b.Spendings
        FROM Bookings_HT b
        JOIN Customers_HT2 c ON b.CustomerID = c.CustomerID
    """)
    bookings = cursor.fetchall()

    return render_template('AdminBookings.html', bookings=bookings)


#Monthly sales
@app.route('/admin/monthly_sales')
def monthly_sales():
    cursor.execute("""
        SELECT DATE_FORMAT(Date, '%Y-%m') AS Month, SUM(Spendings) AS TotalSales
        FROM Bookings_HT
        GROUP BY DATE_FORMAT(Date, '%Y-%m')
        ORDER BY Month;
    """)
    monthly_sales = cursor.fetchall()
    return render_template('MonthlySales.html', monthly_sales=monthly_sales)

#Sales per journey
@app.route('/admin/sales_per_journey')
def sales_per_journey():
    cursor.execute("""
        SELECT Route, SUM(Spendings) AS TotalSales
        FROM Bookings_HT
        GROUP BY Route
        ORDER BY TotalSales DESC;
    """)
    sales_per_journey = cursor.fetchall()
    return render_template('SalesPerJourney.html', sales_per_journey=sales_per_journey)

#Top customer
@app.route('/admin/top_customers')
def top_customers():
    cursor.execute("""
        SELECT c.Name, c.Email, SUM(b.Spendings) AS TotalSpendings
        FROM Customers_HT2 c
        JOIN Bookings_HT b ON c.CustomerID = b.CustomerID
        GROUP BY c.CustomerID
        ORDER BY TotalSpendings DESC
        LIMIT 10;
    """)
    top_customers = cursor.fetchall()
    return render_template('TopCustomers.html', top_customers=top_customers)

#Profitable route
@app.route('/admin/profitable_routes')
def profitable_routes():
    cursor.execute("""
        SELECT f.FlightID, f.Destination, SUM(b.Spendings) AS TotalRevenue, 
               f.Price AS OperatingCost, (SUM(b.Spendings) - f.Price) AS Profit
        FROM Flights_HT f
        LEFT JOIN Bookings_HT b ON f.FlightID = b.Route
        GROUP BY f.FlightID
        HAVING Profit > 0
        ORDER BY Profit DESC;
    """)
    profitable_routes = cursor.fetchall()
    return render_template('ProfitableRoutes.html', profitable_routes=profitable_routes)



#Route Losses
@app.route('/admin/routes_in_loss')
def routes_in_loss():
    cursor.execute("""
        SELECT f.FlightID, f.Destination, SUM(b.Spendings) AS TotalRevenue, 
               f.Price AS OperatingCost, (SUM(b.Spendings) - f.Price) AS Loss
        FROM Flights_HT f
        LEFT JOIN Bookings_HT b ON f.FlightID = b.Route
        GROUP BY f.FlightID
        HAVING Loss < 0
        ORDER BY Loss ASC;
    """)
    routes_in_loss = cursor.fetchall()
    return render_template('RoutesInLoss.html', routes_in_loss=routes_in_loss)



if __name__ == '__main__':
    app.run(debug=True, port=5002)  # Change the port number as needed
