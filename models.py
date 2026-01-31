from extensions import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

    # 👇 NEW
    role = db.Column(db.String(20), default="customer")
    # customer | restaurant_admin | super_admin

    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'))
    restaurant = db.relationship('Restaurant')

class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    image = db.Column(db.String(255))
    cuisine = db.Column(db.String(50))

    is_veg = db.Column(db.Boolean, default=True)
    is_bestseller = db.Column(db.Boolean, default=False)

    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'))

class Cart(db.Model):
    __tablename__ = "cart"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    food_id = db.Column(db.Integer, db.ForeignKey('food.id'))
    quantity = db.Column(db.Integer, default=1)

    food = db.relationship("Food")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total = db.Column(db.Float)
    
    payment_method = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Pending")
    payment_status = db.Column(db.String(20), default="Paid")
    refund_status = db.Column(db.String(20), default="Not Applicable")
    
    created_at = db.Column(db.DateTime, default=db.func.now())

    address = db.Column(db.Text)
    phone = db.Column(db.String(15))

    user = db.relationship('User', backref='orders')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    food_id = db.Column(db.Integer, db.ForeignKey('food.id'))

    food_name = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    food_id = db.Column(db.Integer, db.ForeignKey('food.id'))
    rating = db.Column(db.Integer)  # 1–5
    comment = db.Column(db.Text)

    user = db.relationship('User')
    food = db.relationship('Food')

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Float, default=4.0)
    delivery_time = db.Column(db.String(20), default="30 mins")

    foods = db.relationship('Food', backref='restaurant', lazy=True)

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount = db.Column(db.Integer, nullable=False)  # flat discount amount

class OrderStatusHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    status = db.Column(db.String(20))
    changed_at = db.Column(db.DateTime, default=db.func.now())

    order = db.relationship('Order', backref='status_history')









