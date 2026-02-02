from flask import Flask, render_template, redirect, request,flash,abort,jsonify,url_for,send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (login_user, login_required, logout_user,current_user)
from sqlalchemy import func,or_
import os,io
from extensions import db, login_manager
from models import User, Food, Cart, Order, OrderItem,Restaurant,OrderStatusHistory,Review
from decorators import admin_required
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ---------------- APP CONFIG ---------------- #

app = Flask(__name__)
app.config['SECRET_KEY'] = 'foodapp'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = \
'sqlite:///' + os.path.join(basedir, 'database.db')

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# ---------------- LOGIN ---------------- #

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- CONTEXT ---------------- #

@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        count = db.session.query(func.sum(Cart.quantity)) \
            .filter(Cart.user_id == current_user.id) \
            .scalar()
        return dict(cart_count=count or 0)
    return dict(cart_count=0)

# ---------------- AUTH ---------------- #

@app.route('/')
def home():
    return redirect('/login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']

        # 🔒 Check duplicate username
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash("Username already exists. Choose another.", "error")
            return render_template('register.html')

        user = User(
            username=username,
            password=generate_password_hash(request.form['password'])
        )
        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.", "success")
        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(
            username=request.form['username']
        ).first()

        if user and check_password_hash(
            user.password, request.form['password']
        ):
            login_user(user)
            flash("Login successful", "success")

            # Role-based redirection
            if user.role == "customer":
                return redirect(url_for('menu'))
            elif user.role == "super_admin":
               return redirect(url_for('admin_dashboard'))
            else:
                # fallback if role is unexpected
                return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid username or password", "error")

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# ---------------- MENU ---------------- #

@app.route('/menu')
@login_required
def menu():
    # ✅ Role check
    if current_user.role not in ["customer", "super_admin"]:
        abort(403)

    query = Food.query

    # 1️⃣ Search text (dish name + cuisine)
    search = request.args.get('search', '').strip()
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Food.name.ilike(search_term),
                Food.cuisine.ilike(search_term)
            )
        )
    selected_cuisine = request.args.get('cuisine')
    if selected_cuisine:
        query = query.filter(Food.cuisine == selected_cuisine)

    # 2️⃣ Veg / Non-Veg filter
    food_type = request.args.get('type')
    if food_type == "veg":
        query = query.filter(Food.is_veg == True)
    elif food_type == "nonveg":
        query = query.filter(Food.is_veg == False)

    # 3️⃣ Price range filter
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    if min_price is not None:
        query = query.filter(Food.price >= min_price)
    if max_price is not None:
        query = query.filter(Food.price <= max_price)

    # 4️⃣ Sort by price
    sort = request.args.get('sort', '')
    if sort == 'low':
        query = query.order_by(Food.price.asc())
    elif sort == 'high':
        query = query.order_by(Food.price.desc())

    foods = query.all()

    # ---------------- RESTAURANT GROUPING ----------------
    restaurants = {}
    for food in foods:
        avg_rating = db.session.query(func.avg(Review.rating)) \
            .filter(Review.food_id == food.id).scalar()
        food.avg_rating = round(avg_rating, 1) if avg_rating else None

        if food.restaurant:
            restaurants.setdefault(food.restaurant, []).append(food)

    # ---------------- CART MAP ----------------
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    cart_map = {item.food_id: item.quantity for item in cart_items}

    # ---------------- CUISINE GROUPING ----------------
    cuisines = {}
    for food in foods:
        cuisines.setdefault(food.cuisine, []).append(food)

    # All cuisines for dropdown
    all_cuisines = db.session.query(Food.cuisine).distinct().all()
    all_cuisines = [c[0] for c in all_cuisines]

    # ---------------- Recommendations ----------------
    recommendations = []
    if current_user.role == "customer":
        recommendations = get_user_recommendations(current_user.id)

    return render_template(
        'menu.html',
        restaurants=restaurants,
        cuisines=cuisines,
        all_cuisines=all_cuisines,
        cart_map=cart_map,
        recommendations=recommendations,
        search=search,
        selected_cuisine=selected_cuisine
    )


@app.route('/food/<int:food_id>')
@login_required
def food_details(food_id):

    food = Food.query.get_or_404(food_id)

    reviews = Review.query.filter_by(food_id=food.id).all()
    avg_rating = None

    if reviews:
        avg_rating = round(sum([r.rating for r in reviews]) / len(reviews), 1)

    return render_template("food_details.html",
                           food=food,
                           reviews=reviews,
                           avg_rating=avg_rating)

# ---------------- CART ---------------- #

@app.route('/add/<int:id>')
@login_required
def add(id):
    item = Cart.query.filter_by(
        user_id=current_user.id,
        food_id=id
    ).first()

    if item:
        item.quantity += 1
    else:
        item = Cart(
            user_id=current_user.id,
            food_id=id,
            quantity=1
        )
        db.session.add(item)

    db.session.commit()
    return redirect('/menu')


@app.route('/cart')
@login_required
def cart():
    if current_user.role not in ["customer", "super_admin"]:
        abort(403)

    items = Cart.query.filter_by(user_id=current_user.id).all()

    total = sum(item.food.price * item.quantity for item in items)

    # Default (no coupon)
    discount = 0
    final_total = total

    return render_template(
        'cart.html',
        cart_items=items,   
        total=total,
        discount=discount,
        final_total=final_total
    )


@app.route('/increase/<int:id>')
@login_required
def increase(id):
    item = Cart.query.get(id)
    item.quantity += 1
    db.session.commit()
    return redirect('/cart')


@app.route('/decrease/<int:id>')
@login_required
def decrease(id):
    item = Cart.query.get(id)
    if item.quantity > 1:
        item.quantity -= 1
    else:
        db.session.delete(item)
    db.session.commit()
    return redirect('/cart')


@app.route('/remove/<int:id>')
@login_required
def remove(id):
    item = Cart.query.get(id)
    db.session.delete(item)
    db.session.commit()
    return redirect('/cart')

# ---------------- PAYMENT & ORDER ---------------- #

@app.route('/payment')
@login_required
def payment():
    items = Cart.query.filter_by(
        user_id=current_user.id
    ).all()

    total = sum(
        item.food.price * item.quantity
        for item in items
    )

    return render_template(
        'payment.html',
        items=items,
        total=total
    )

@app.route('/order')
@login_required
def order():
    cart_items = Cart.query.filter_by(
        user_id=current_user.id
    ).all()

    if not cart_items:
        return redirect('/cart')

    # ✅ ADD THIS LINE HERE
    payment_method = request.args.get('payment_method', 'cod')
    address = request.args.get('address')
    phone = request.args.get('phone')

    total = sum(
        item.food.price * item.quantity
        for item in cart_items
    )

    order = Order(
        user_id=current_user.id,
        total=total,
        payment_method=payment_method,
        status='Pending',
        address=address,
        phone=phone
    )
    db.session.add(order)
    db.session.commit()

    history = OrderStatusHistory(
        order_id=order.id,
        status='Pending'
    )
    db.session.add(history)
    db.session.commit() 

    for item in cart_items:
        db.session.add(OrderItem(
        order_id=order.id,
        food_id=item.food.id,
        food_name=item.food.name,
        price=item.food.price,
        quantity=item.quantity
    ))

    Cart.query.filter_by(
        user_id=current_user.id
    ).delete()

    db.session.commit()

    return render_template(
        'order_success.html',
        order=order,
        payment_method=payment_method
    )

@app.route('/orders')
@login_required
def orders():
    if current_user.role not in ["customer", "super_admin"]:
        abort(403)

    # 🔹 Step 1: Fetch user’s reviewed food IDs
    reviewed_food_ids = {
        r.food_id
        for r in Review.query.filter_by(user_id=current_user.id).all()
    }

    review_map = {
        r.food_id: r.rating
        for r in Review.query.filter_by(user_id=current_user.id).all()
    }


    # 🔹 Step 2: Fetch orders
    orders = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(Order.id.desc()).all()

    data = []
    for order in orders:
        # Build items with reviewed flag
        items = []

        for item in OrderItem.query.filter_by(order_id=order.id).all():
            items.append({
                "food_id": item.food_id,
                "food_name": item.food.name if hasattr(item, "food") else "",
                "quantity": item.quantity,
                "price": item.price,
                "reviewed": item.food_id in reviewed_food_ids
            })

        # Status history
        history = OrderStatusHistory.query \
            .filter_by(order_id=order.id) \
            .order_by(OrderStatusHistory.changed_at.asc()) \
            .all()

        data.append({
            "order": order,
            "items": items,
            "history": history
        })

    # 🔹 Step 3: Pass reviewed_food_ids into template
    return render_template(
        'orders.html',
        data=data,
        reviewed_food_ids=reviewed_food_ids,
        review_map=review_map
    )


# ---------------- ADMIN ---------------- #

@app.route("/admin", methods=["GET", "POST"])
@login_required
@admin_required
def admin():
    if request.method == "POST":        
        if current_user.restaurant_id:
            restaurant_id = current_user.restaurant_id
        else:
            restaurant_id = request.form["restaurant_id"]

        food = Food(
            name=request.form["name"],
            price=request.form["price"],
            image=request.form["image"],
            cuisine=request.form["cuisine"],
            restaurant_id=restaurant_id,
            is_veg="is_veg" in request.form,
            is_bestseller="is_bestseller" in request.form
        )
        db.session.add(food)
        db.session.commit()

        flash("Dish added successfully", "success")
        return redirect("/admin")

    if current_user.role == "restaurant_admin":
        foods = Food.query.filter_by(
            restaurant_id=current_user.restaurant_id
        ).all()
        restaurants = []
    else:
        foods = Food.query.all()
        restaurants = Restaurant.query.all()
    
    return render_template("admin.html", foods=foods, restaurants=restaurants)

@app.route('/admin/delete/<int:id>')
@login_required
@admin_required
def delete_food(id):
    food = Food.query.get_or_404(id)
    db.session.delete(food)
    db.session.commit()
    return redirect('/admin')

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.count()

    # Role-based logic for orders and revenue
    if current_user.role == "restaurant_admin":
        total_orders = (
            db.session.query(Order)
            .join(OrderItem)
            .join(Food)
            .filter(Food.restaurant_id == current_user.restaurant_id)
            .distinct()
            .count()
        )

        total_revenue = (
            db.session.query(func.sum(OrderItem.price * OrderItem.quantity))
            .join(Food)
            .filter(Food.restaurant_id == current_user.restaurant_id)
            .scalar()
        ) or 0
    else:
        total_orders = Order.query.count()
        total_revenue = db.session.query(func.sum(Order.total)).scalar() or 0

    # Top foods (you may also want to filter by restaurant if admin is restaurant-specific)
    top_foods = (
        db.session.query(
            OrderItem.food_name,
            func.sum(OrderItem.quantity).label('qty')
        )
        .group_by(OrderItem.food_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )

    # Recent orders (same note: could filter by restaurant if needed)
    recent_orders = (
        Order.query
        .order_by(Order.id.desc())
        .limit(5)
        .all()
    )

    return render_template(
        'dashboard.html',
        total_users=total_users,
        total_orders=total_orders,
        total_revenue=total_revenue,
        top_foods=top_foods,
        recent_orders=recent_orders
    )


@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():

    if current_user.role == "restaurant_admin":
        orders = (
            db.session.query(Order)
            .join(OrderItem)
            .join(Food)
            .filter(Food.restaurant_id == current_user.restaurant_id)
            .distinct()
            .order_by(Order.id.desc())
            .all()
        )
    else:
        orders = Order.query.order_by(Order.id.desc()).all()

    data = []
    for order in orders:
        items = OrderItem.query.filter_by(order_id=order.id).all()
        data.append({
            'order': order,
            'items': items,
            'user': order.user
        })

    return render_template('admin_orders.html', data=data)

@app.route('/admin/update-order-status/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):  
    order = Order.query.get(order_id)
    if order:
        new_status = request.form.get('status')
        order.status = new_status
        history = OrderStatusHistory(
            order_id=order.id,
            status=new_status
        )
        db.session.add(history)
        db.session.commit()
    flash("Order status updated", "success")
    return redirect('/admin/orders')

@app.route('/admin/cancel-order/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def cancel_order(order_id):
    order = Order.query.get(order_id)
    if order:
        order.status = 'Cancelled'
        history = OrderStatusHistory(
            order_id=order.id,
            status='Cancelled'
        )
        db.session.add(history)
        db.session.commit()
    flash("Order cancelled", "success")
    return redirect('/admin/orders')


@app.route('/profile')
@login_required
def profile():
    total_orders = Order.query.filter_by(
        user_id=current_user.id
    ).count()

    total_spent = db.session.query(
        func.sum(Order.total)
    ).filter(
        Order.user_id == current_user.id
    ).scalar() or 0

    last_order = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(Order.id.desc()).first()

    return render_template(
        'profile.html',
        user=current_user,
        total_orders=total_orders,
        total_spent=total_spent,
        last_order=last_order
    )

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        if check_password_hash(
            current_user.password,
            request.form['old_password']
        ):
            current_user.password = generate_password_hash(
                request.form['new_password']
            )
            db.session.commit()
            flash("Password updated successfully", "success")
            return redirect('/profile')
        else:
            flash("Old password is incorrect", "error")

    return render_template('change_password.html')


@app.route('/payment/online', methods=['GET', 'POST'])
@login_required
def online_payment():
    items = Cart.query.filter_by(
        user_id=current_user.id
    ).all()

    if not items:
        return redirect('/cart')

    total = sum(
        item.food.price * item.quantity
        for item in items
    )

    # Demo payment success
    if request.method == 'POST':
        return redirect('/order?payment_method=online')

    return render_template(
        'online_payment.html',
        total=total
    )

@app.route('/review/<int:food_id>', methods=['POST'])
@login_required
def add_review(food_id):

    # Allow review only if delivered
    delivered = db.session.query(OrderItem) \
        .join(Order) \
        .filter(
            Order.user_id == current_user.id,
            Order.status == 'Delivered',
            OrderItem.food_id == food_id
        ).first()

    if not delivered:
        flash("You can review only delivered orders.")
        return redirect('/orders')

    # Prevent duplicate review
    existing = Review.query.filter_by(
        user_id=current_user.id,
        food_id=food_id
    ).first()

    if existing:
        flash("You already reviewed this item.","info")
        return redirect('/orders')

    review = Review(
        user_id=current_user.id,
        food_id=food_id,
        rating=int(request.form['rating']),
        comment=request.form['comment']
    )

    db.session.add(review)
    db.session.commit()

    flash("✅ Review submitted successfully!")
    return redirect('/orders')

# ➕ Increase quantity (AJAX)
@app.route('/api/cart/add/<int:food_id>', methods=['POST'])
@login_required
def api_add_to_cart(food_id):
    item = Cart.query.filter_by(
        user_id=current_user.id,
        food_id=food_id
    ).first()

    if item:
        item.quantity += 1
    else:
        item = Cart(
            user_id=current_user.id,
            food_id=food_id,
            quantity=1
        )
        db.session.add(item)

    db.session.commit()

    return jsonify({
        "success": True,
        "quantity": item.quantity
    })

# ➖ Decrease quantity (AJAX)
@app.route('/api/cart/remove/<int:food_id>', methods=['POST'])
@login_required
def api_remove_from_cart(food_id):
    item = Cart.query.filter_by(
        user_id=current_user.id,
        food_id=food_id
    ).first()

    if not item:
        return jsonify({"success": True, "quantity": 0})

    if item.quantity > 1:
        item.quantity -= 1
        db.session.commit()
        return jsonify({"success": True, "quantity": item.quantity})
    else:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True, "quantity": 0})

@app.route('/api/order-status/<int:order_id>')
@login_required
def api_order_status(order_id):
    order=Order.query.get(order_id)
    if not order or order.user_id!=current_user.id:
        return jsonify({"success":False})
    return jsonify({
        "success":True,
        "status":order.status
    })

@app.route('/cancel-order/<int:order_id>', methods=['POST'])
@login_required
def user_cancel_order(order_id):

    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        abort(403)

    if order.status not in ['Pending', 'Accepted']:
        flash("Order cannot be cancelled now.", "danger")
        return redirect('/orders')

    order.status = 'Cancelled'

    # ✅ REFUND LOGIC (THIS WAS MISSING)
    if order.payment_method.lower() == "online":
        order.payment_status = "Refunded"
        order.refund_status = "Refund Initiated (Mock)"

    history = OrderStatusHistory(
        order_id=order.id,
        status='Cancelled'
    )
    db.session.add(history)
    db.session.commit()

    flash("Order cancelled successfully.", "success")
    return redirect('/orders')


@app.route('/create-default-restaurant')
def create_default_restaurant():
    r = Restaurant(
        name="Main Restaurant",
        rating=4.3,
        delivery_time="30 mins"
    )
    db.session.add(r)
    db.session.commit()
    return "Default restaurant created"


@app.route('/apply_coupon', methods=['POST'])
@login_required
def apply_coupon():
    code = request.form.get('coupon_code').strip().upper()

    items = Cart.query.filter_by(user_id=current_user.id).all()

    if not items:
        return redirect('/cart')

    total = sum(item.food.price * item.quantity for item in items)

    discount = 0
    coupon_msg = None
    coupon_error = None

    # Example coupon
    if code == "SAVE50":
        discount = 50
        coupon_msg = "Coupon applied! ₹50 OFF"
        flash("Coupon applied successfully", "success")
    else:
        coupon_error = "Invalid coupon code"
        flash("Invalid coupon code", "error")

    final_total = max(total - discount, 0)

    # 🔑 IMPORTANT: Do NOT clear cart here

    return render_template(
        'cart.html',
        cart_items=items,   # 👈 change key name
        total=total,
        discount=discount,
        final_total=final_total,
        coupon_msg=coupon_msg,
        coupon_error=coupon_error
    )

@app.route('/create-restaurant-admin')
def create_restaurant_admin():
    admin = User(
        username="pizza_admin",
        password=generate_password_hash("1234"),
        role="restaurant_admin",
        restaurant_id=1
    )
    db.session.add(admin)
    db.session.commit()
    return "Restaurant admin created"

def get_user_recommendations(user_id, limit=3):
    # 1️⃣ Foods ordered by user
    ordered_food_ids = (
        db.session.query(OrderItem.food_id)
        .join(Order)
        .filter(Order.user_id == user_id)
        .distinct()
        .all()
    )

    ordered_food_ids = [f[0] for f in ordered_food_ids]

    if ordered_food_ids:
        # 2️⃣ Get cuisines user likes
        cuisines = (
            db.session.query(Food.cuisine)
            .filter(Food.id.in_(ordered_food_ids))
            .distinct()
            .all()
        )

        cuisines = [c[0] for c in cuisines]

        # 3️⃣ Recommend similar cuisine foods
        recommendations = (
            Food.query
            .filter(
                Food.cuisine.in_(cuisines),
                Food.id.notin_(ordered_food_ids)
            )
            .limit(limit)
            .all()
        )

        if recommendations:
            return recommendations

    # 4️⃣ Fallback → popular items
    popular_items = (
        db.session.query(Food)
        .join(OrderItem)
        .group_by(Food.id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )

    return popular_items

@app.template_filter('highlight')
def highlight(text, word):
    if not word:
        return text
    return text.replace(
        word,
        f"<mark>{word}</mark>"
    )

@app.route("/invoice/<int:order_id>")
@login_required
def generate_invoice(order_id):
    order = Order.query.get_or_404(order_id)

    # Security: customer can download only their own invoice
    if order.user_id != current_user.id and current_user.role == "Customer":
        abort(403)

    # ✅ FIX: fetch items manually
    order_items = OrderItem.query.filter_by(order_id=order.id).all()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    # Title
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(180, y, "FoodHub Invoice")
    y -= 40

    # Order info
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, y, f"Order ID: {order.id}")
    y -= 20
    pdf.drawString(50, y, f"Payment Method: {order.payment_method.upper()}")
    y -= 20
    pdf.drawString(50, y, f"Delivery Address: {order.address}")
    y -= 30

    # Table header
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Item")
    pdf.drawString(260, y, "Qty")
    pdf.drawString(310, y, "Price")
    pdf.drawString(390, y, "Total")
    y -= 20

    pdf.setFont("Helvetica", 11)

    subtotal = 0

    for item in order_items:
        item_total = item.price * item.quantity
        subtotal += item_total

        pdf.drawString(50, y, item.food_name)
        pdf.drawString(260, y, str(item.quantity))
        pdf.drawString(310, y, f"₹{item.price}")
        pdf.drawString(390, y, f"₹{item_total}")
        y -= 20

        if y < 100:
            pdf.showPage()
            y = height - 50

    # Charges
    gst = round(subtotal * 0.05, 2)
    delivery_charge = 40 if subtotal < 500 else 0
    final_amount = subtotal + gst + delivery_charge

    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(300, y, "Subtotal:")
    pdf.drawString(390, y, f"₹{subtotal}")
    y -= 20
    pdf.drawString(300, y, "GST (5%):")
    pdf.drawString(390, y, f"₹{gst}")
    y -= 20
    pdf.drawString(300, y, "Delivery:")
    pdf.drawString(390, y, f"₹{delivery_charge}")
    y -= 20
    pdf.drawString(300, y, "Final Amount:")
    pdf.drawString(390, y, f"₹{final_amount}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"FoodHub_Invoice_Order_{order.id}.pdf",
        mimetype="application/pdf"
    )


# ---------------- RUN ---------------- #

if __name__ == '__main__':
    app.run(debug=True)