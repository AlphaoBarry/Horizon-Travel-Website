# Horizon Travel – Flight Booking Web App ✈️

A full-stack web application built with **Flask (Python)** for booking flights, managing customers, and generating QR codes for tickets.  
Includes **user authentication, password hashing, discounts, and admin dashboards** for sales and route analysis.

---

## Features 
- **User Authentication**  
  - Secure sign-up and login with password hashing (bcrypt).  
  - Session-based authentication with role-based access (customer vs admin).  

- **Flight Booking System**  
  - Search and book flights (Economy & Business).  
  - Automatic price calculation with discounts based on booking date.  
  - QR code generation for each booking.  
  - Update or cancel bookings.  

- **Customer Portal**  
  - View personal details and booking history.  
  - Change password securely.  

- **Admin Dashboard**  
  - Manage flights, bookings, and customers.  
  - View sales reports: monthly sales, top customers, profitable/loss-making routes.  

---

## Tech Stack 
- **Backend**: Python, Flask  
- **Frontend**: HTML, CSS (Jinja2 templates)  
- **Database**: MySQL (via custom `DBfunc.py`)  
- **Authentication**: bcrypt  
- **Email Service**: Flask-Mail  
- **Other Tools**: QRCode, Flask session management  

---
Screenshots


## Installation 
1. Clone the repo:
   ```bash
   git clone https://github.com/AlphaoBarry/Horizon-Travel-Website.git
   cd Horizon-Travel-Website
