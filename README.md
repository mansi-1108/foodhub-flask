# 🍔 FoodHub – Online Food Ordering System

FoodHub is a full-stack online food ordering web application built using Flask, SQLAlchemy, and JavaScript.
It provides a real-world food delivery experience with cart management, live order tracking, admin controls, and invoice generation.

## 🚀 Key Features

- User authentication (Customer, Restaurant Admin, Super Admin)
- Restaurant-wise menu browsing with filters
- Add to cart and quantity management
- 🔄 Real-time cart count update using AJAX (no page reload)
- Secure checkout with Cash on Delivery and Online Payment
- 🧾 Downloadable order invoice (PDF)
- Live order tracking with status timeline
- Order cancellation with refund logic
- Reviews and ratings after delivery

## 🧾 Order Invoice (PDF)

After successful order placement, users can download a detailed invoice.

Invoice includes:
- Order ID
- Customer details
- Ordered items with quantity and price
- GST calculation
- Delivery charges
- Final payable amount

Tech Used:
- Python ReportLab for PDF generation
- Secure access (only order owner can download)

## 🔄 Real-Time Cart Update

- Cart item count updates instantly using AJAX
- No page reload required
- Improves user experience and performance

## 🛠️ Admin Features

- Admin dashboard for orders and revenue
- Manage menus and food items
- Update order status (Accepted → Preparing → Delivered)
- View complete order history
- Status timeline and audit tracking

## 🛠️ Tech Stack

- Backend: Flask, SQLAlchemy
- Frontend: HTML, CSS, JavaScript (AJAX)
- Database: SQLite
- Authentication: Flask-Login
- PDF Generation: ReportLab

## ▶️ How to Run Locally

Clone the repository  
git clone https://github.com/mansi-1108/foodhub-flask.git

Navigate to project folder  
cd foodhub-flask

Create virtual environment  
python -m venv venv  
venv\Scripts\activate   (Windows)

Install dependencies  
pip install -r requirements.txt

Run the application  
python app.py

App will run at:  
http://127.0.0.1:5000

## 📸 Screenshots

Home Page  
screenshots/home.png

Login Page  
screenshots/login.png

Register Page  
screenshots/register.png

Menu Page  
screenshots/menu.png

Cart Page  
screenshots/cart.png

Order Page  
screenshots/order.png

Invoice Download  
screenshots/invoice.png

Admin Dashboard  
screenshots/dashboard.png

## ❌ Order Cancellation & Refund Logic

- Orders can be cancelled only before food preparation
- Cancellation automatically updates order status
- Mock refund initiated for online payments
- COD orders do not trigger refunds
- Complete status history stored for tracking
