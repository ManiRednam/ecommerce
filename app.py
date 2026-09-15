from flask import Flask, render_template, redirect, url_for, request, make_response, flash, jsonify

import jwt
from datetime import datetime, timedelta, timezone

from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
import uuid

# ------------import database logics -------------------
from database.tables import createTables
from database.utility import checkUserExists, addUser, getUserDetails, getCatagoriesFromDB, getProductsFromDB
from database.utility import addProductToDB, totalOrdersCount, getOrders, usersDetails, getUserDetailsByID, updateAdminProfile
from database.utility import getProductDetailsByID, updateProductInfo, updateProductStatus, viewUserByAdmin, viewOrderDetails, totalProducts
from database.utility import getOrderById, updateOrderPaymentStatus, markOrderPaymentFailure
from database.userutility import createPendingOrder, finalizePaidOrder
from services.razorpay_service import create_payment_order, verify_payment_signature

from database.connection import ensure_database_exists

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')



## -------------------------- Helper Functions ------------------------------------


## token protection decorator
def token_required(role=None):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.cookies.get('token')

            if not token:
                flash('Please login to continue.', 'danger')
                return redirect(url_for('login'))

            try:
                data = jwt.decode(
                    token,
                    app.config['SECRET_KEY'],
                    algorithms=["HS256"]
                )
            except jwt.ExpiredSignatureError:
                flash('Your session has expired. Please login again.', 'warning')
                return redirect(url_for('login'))
            except jwt.InvalidTokenError:
                flash('Invalid session. Please login again.', 'warning')
                return redirect(url_for('login'))

            user_role = (data.get('role') or '').lower()
            if role and user_role != role.lower():
                flash('Unauthorized access.', 'danger')
                return redirect(url_for('login'))

            return f(*args, **kwargs)
        return decorated
    return wrapper


def getUserByToken():
    token = request.cookies.get('token')

    if not token:
        return None

    try:
        data = jwt.decode(
            token,
            app.config['SECRET_KEY'],
            algorithms=["HS256"]
        )

        user_id = data.get('user_id')
        user = getUserDetailsByID(user_id=user_id)

        if not user:
            return None

        user['USER_ID'] = user.get('USER_ID') or user.get('user_id')
        user['USERID'] = user['USER_ID']
        user['userid'] = user['USER_ID']

        user['ROLE'] = user.get('ROLE') or user.get('role')
        user['role'] = user['ROLE']

        user['NAME'] = user.get('NAME') or user.get('name')
        user['name'] = user['NAME']

        user['EMAIL'] = user.get('EMAIL') or user.get('email')
        user['email'] = user['EMAIL']

        user['PHONE_NUMBER'] = user.get('PHONE_NUMBER') or user.get('phone_number') or user.get('phone')
        user['phone'] = user['PHONE_NUMBER']

        user['PASSWORD'] = user.get('PASSWORD') or user.get('password')
        user['password'] = user['PASSWORD']

        user['PROFILE_IMAGE'] = user.get('PROFILE_IMAGE') or user.get('profile_image')
        user['profile_image'] = user['PROFILE_IMAGE']

        return user

    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None



# index route
@app.route('/')
def index():
    return render_template('user/user_home.html',
                            user_logged_in=False)


# login route
@app.route("/login", methods=['GET',"POST"])
def login():
    # if it is POST request method
    # get form data
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
       
        # user validation
        data = getUserDetails(email=username)
        # print(data)
        if data and check_password_hash(data['password'], password):
            
            # create login token
            # utc_now = datetime.now(timezone.utc)

            # Add 2 hours
            exp_time = datetime.now(timezone.utc) + timedelta(hours=2)

            token = jwt.encode(
                {
                    "user_id": data["user_id"],
                    "role": data["role"],
                    "exp": exp_time,
                    "username":data['name']
                },
                app.config['SECRET_KEY'],
                algorithm="HS256"
            )

             # Based on role it selects the user dashbord or admin dashboard
            response = make_response(
                redirect(url_for('admin' if data['role']=='admin' else 'user'))
            )

            # store token in cookie
            response.set_cookie(
                'token',
                token,
                httponly=True,
                secure=False  # True in production (HTTPS)
            )

            return response
        # If credintial is incorrect
        flash('User Credentials incorrect')
        return redirect(url_for('login'))

    # if it is get request 
    return render_template('login.html')


# ---------------------- images upload path ------------------
PROFILE_UPLOAD_FOLDER = 'static/uploads/profile'
PRODUCT_UPLOAD_FOLDER = 'static/uploads/products'

app.config['PROFILE_UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'profiles')
app.config['PRODUCT_UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'products')
os.makedirs(app.config['PRODUCT_UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# ------------------------------------------------------------
#registe Route
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        profile_image = request.files.get('profile_image')

        # basic validation
        if not name or not email or not phone or not password:
            flash("All required fields must be filled")
            return redirect(url_for('register'))

        # check user already exists
        if checkUserExists(email=email):
            flash("Email already registered")
            return redirect(url_for('register'))

        # password hash
        hashed_password = generate_password_hash(password)

        # handle profile image
        image_path = None
        if profile_image and profile_image.filename != "":
            if allowed_file(profile_image.filename):
                filename = secure_filename(profile_image.filename)
                os.makedirs(app.config['PROFILE_UPLOAD_FOLDER'], exist_ok=True)

                image_path = os.path.join(
                    app.config['PROFILE_UPLOAD_FOLDER'],
                    filename
                )

                profile_image.save(image_path)
            else:
                flash("Invalid image format")
                return redirect(url_for('register'))

        # add user to database
        addUser(
            name=name,
            email=email,
            phone_number=phone,
            password=hashed_password,
            profile_image=image_path
        )

        flash("Registration successful. Please login.")
        return redirect(url_for('login'))

    return render_template('register.html')

# forgotpassword route
@app.route('/forgotpassword')
def forgotpassword():
    return "forgot Password Page"



## Admin Routes
# admin dashborad route
@app.route('/admin')
@token_required(role='admin')
def admin():

    total_products = totalProducts() # need to update in utilituy
    total_orders = totalOrdersCount()
    pending_orders = totalOrdersCount(status="PENDING") # need to update in utilituy
    total_users = len(usersDetails()) # need to update in utilituy
    return render_template('admin/dashboard.html',
                            total_products=total_products,
                            total_orders=total_orders,
                            pending_orders=pending_orders,
                            total_users=total_users
                        )

# product route

@app.route('/admin/products')
@token_required(role='admin')
def adminproducts():
    # get all categories name 
    categories = getCatagoriesFromDB()

    product_name = request.args.get('name',"")
    category = request.args.get('category', "")
    status = request.args.get('status', "")

    # print(category, product_name, status)
    # Get all products from  database
    products = getProductsFromDB(name=product_name, category= category, status= status)
    # print(products)
    return render_template('admin/products.html', categories= categories, products=products)

# Add product Route

@app.route('/admin/addproduct', methods = ['GET','POST'])
@token_required(role='admin')
def adminaddproduct():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        active = request.form['active']
        price = request.form['price']
        stock = request.form['stock']
        image = request.files.get('image')
        new_category = request.form.get('new_category')
        # check if new category is avialable or not 
        # if new_category:
        #     category = new_category
        if category == "new" and new_category:
            category = new_category
        # print("******************************")
        # print("--------- DEBUG START ---------")
        # print("request.files:", request.files)
        # print("image object:", image)
        # print("image filename:", image.filename if image else "NO IMAGE")
        # print("PRODUCT_UPLOAD_FOLDER:", app.config.get('PRODUCT_UPLOAD_FOLDER'))
        # print("--------------------------------")

        image_path = None


        if image and image.filename != '':

            ext = image.filename.rsplit('.', 1)[1].lower()

            if ext in ALLOWED_EXTENSIONS:

                filename = str(uuid.uuid4()) + "_" + secure_filename(image.filename)
                print(filename)
                save_path = os.path.join(
                    app.config['PRODUCT_UPLOAD_FOLDER'],
                    filename
                )
                print(save_path)
                image.save(save_path)
                print("saved")
                # Save relative path in DB
                image_path = f"uploads/products/{filename}"

        
        # add procuts details into products table
        addProductToDB(name=name,
                       description=description,
                       category=category,
                       price=price,
                       stock=stock,
                       active=active,
                       image_url=image_path)
        flash("Product added successfully","success")
        return redirect(url_for('adminproducts')) # after redirect to products page

    return render_template('admin/addproduct.html', categories = getCatagoriesFromDB())


@app.route('/admin/editproduct/<int:productid>', methods=['GET', 'POST'])
@token_required(role='admin')
def editproduct(productid):
    # get product data from database
    product = getProductDetailsByID(productid=productid)
    # if request is post 
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        price = request.form.get('price')
        stock = request.form.get('stock')
        active = request.form.get('active')
        # update with new data in database
        if updateProductInfo(name, description,category, price, stock, active, productid):
            flash("Product updated successfully", "success")
            return redirect(url_for('adminproducts'))
        flash("Product NoT updated", "Error")
        return redirect(url_for('adminproducts'))

    return render_template('admin/edit_products.html',product = product)

# deactivate user
# view user 
@app.route('/admin/deactivate_product/<int:productid>', methods=['POST'])
@token_required(role='admin')
def deactivate_product(productid):
    # update in database
    status = updateProductStatus(productid=productid, status=0)
    if status:
        flash("Product deactivated successfully", "warning")
        return redirect(url_for('adminproducts'))
    flash("Product Not deactivated", "Error")
    return redirect(url_for('adminproducts'))
    
@app.route('/admin/activate_product/<int:productid>', methods=['POST'])
@token_required(role='admin')
def activate_product(productid):
    # update in database
    status = updateProductStatus(productid=productid, status=1)
    if status:
        flash("Product Activates successfully", "warning")
        return redirect(url_for('adminproducts'))
    flash("Product Not activated", "Error")
    return redirect(url_for('adminproducts'))
    

@app.route('/admin/users')
@token_required(role='admin')
def adminusers():

    # filters
    name = request.args.get('name', '').strip()
    email = request.args.get('email', '').strip()
    role = request.args.get('role', '').strip()
    users = usersDetails(name=name, email=email, role=role)
    

    return render_template(
        "admin/users.html",
        users=users,
        total_users=len(users)
    )


# orders Route

@app.route('/admin/orders')
@token_required(role='admin')
def adminorders():
    # get filter parameter 
    orderid = request.args.get('orderid',"")
    product_name = request.args.get('productname',"")
    from_date = request.args.get('fromdate',"")
    to_date = request.args.get('todate',"")

    orders_count = totalOrdersCount()
    # getting filterd orders
    orders = getOrders(orderid=orderid,
                       product_name=product_name,
                       from_date=from_date,
                       to_date=to_date)
    filter_orders_count = len(orders)
    # print(orders[:3])

    return render_template('admin/orders.html',
                            total_orders=orders_count,
                            filtered_order_count=filter_orders_count,
                            orders=orders)


# view order
@app.route('/admin/view-Order/<int:order_id>', methods=['GET', 'POST'])
@token_required(role='admin')
def view_order(order_id):
    order, items = viewOrderDetails(order_id)

    return render_template(
        'admin/view_orders.html',
        order=order,
        items=items
    )
# view user 
@app.route('/admin/viewuser/<int:user_id>', methods=['GET', 'POST'])
@token_required(role='admin')
def view_user(user_id):

    # get user data from database
    user = viewUserByAdmin(user_id=user_id)
    if not user:
        flash("User not found", "danger")
        return redirect(url_for('adminusers'))

    return render_template('admin/view_user.html',user=user
    )
    

# deactivate user
# view user 
@app.route('/admin/deactivate/<int:user_id>', methods=['GET', 'POST'])
@token_required(role='admin')
def deactivate_user(user_id):
    return "deactivate user"


# admin profile route

@app.route('/admin/profile', methods=['GET', 'POST'])
@token_required(role='admin')
def adminprofile():

    user = getUserByToken()   # helper → decodes token, returns user data

    if request.method == 'POST':

        name = request.form.get('name')
        phone = request.form.get('phone')

        updateAdminProfile(
            userid=user['userid'],
            name=name,
            phone=phone
        )

        flash("Profile updated successfully", "success")
        return redirect(url_for('adminprofile'))

    return render_template(
        'admin/profile.html',
        user=user
    )



@app.route('/admin/change-password', methods=['POST'])
@token_required(role='admin')
def admin_change_password():
    user = getUserByToken()
    if not user:
        flash('Please login to update your password.', 'warning')
        return redirect(url_for('login'))

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')

    if not current_password or not new_password:
        flash('Current password and new password are required.', 'danger')
        return redirect(url_for('adminprofile'))

    if not check_password_hash(user['PASSWORD'], current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('adminprofile'))

    hashed_password = generate_password_hash(new_password)
    updateAdminProfile(user_id=user['USERID'], new_password=hashed_password)
    flash('Password updated successfully.', 'success')
    return redirect(url_for('adminprofile'))



@app.route('/admin/logout')
def adminlogout():
    response = make_response(redirect(url_for('login')))

    # delete token cookie
    response.set_cookie(
        'token',
        '',
        expires=0,
        httponly=True
    )

    return response


# --------------------------------User Routes --------------------------------#

# get user utility database fuctions from database
from database.userutility import getProductsByCategory, getProductById,getCartItem,increaseCartQuantity, insertCartItem
from database.userutility import getUserCartItems, removeFromCart, updateCartQuantity, getProductsBasedOnSearch, getCartItems, placeOrder
from database.userutility import myOrders, getProductsByCategory, getProductById, getCartItem, increaseCartQuantity, insertCartItem, getUserCartItems


# helper fucntion 
def getDataFromToken():
    token = request.cookies.get('token')

    if not token:
        return redirect(url_for('login'))

    try:
        data = jwt.decode(
            token,
            app.config['SECRET_KEY'],
            algorithms=["HS256"]
        )
        normalized = dict(data)
        user_id = normalized.get('user_id') or normalized.get('USER_ID') or normalized.get('USERID')
        if user_id is not None:
            normalized['user_id'] = user_id
            normalized['USER_ID'] = user_id
            normalized['USERID'] = user_id
            normalized['userid'] = user_id
        role = normalized.get('role') or normalized.get('ROLE')
        if role is not None:
            normalized['role'] = role
            normalized['ROLE'] = role
        return normalized
    except jwt.ExpiredSignatureError:
        return redirect(url_for('login'))
    except jwt.InvalidTokenError:
        return redirect(url_for('login'))
    

#User dashboard route

@app.route('/user')
@token_required(role='user')
def user():
    user = getUserByToken()
    name = user.get('NAME','Dear User')
    # print(user)
    return render_template('user/user_home.html',
                            user_logged_in=True,
                            username=name)

#User dashboard route

@app.route('/user/search')
@token_required(role='user')
def search():
    q = request.args.get('q', None)
    if q:
        products = getProductsBasedOnSearch(product_name=q)
        return render_template('user/category_products.html', products=products, category=q, user_logged_in=True,
)
    return render_template('user/user_home.html')


#home route
# @token_required(role='user')
# @app.route('/user/home')
# def user_home():
#     return "user home page"

@app.route('/category/<string:category_name>')
def category_products(category_name):
    
    user = getUserByToken()
    
    # Handle user safely
    if user:
        name = user.get('NAME', 'Dear User')
        user_logged_in = True
    else:
        name = 'Dear User'
        user_logged_in = False

    # Get query parameters
    sort = request.args.get('sort')
    
    # Convert price filters safely
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')

    try:
        min_price = float(min_price) if min_price else None
        max_price = float(max_price) if max_price else None
    except ValueError:
        min_price = None
        max_price = None

    # Fetch products
    products = getProductsByCategory(category_name, min_price, max_price, sort)

    return render_template(
        'user/category_products.html',
        products=products,
        category=category_name,
        user_logged_in=user_logged_in,
        username=name
    )
# user product details 
@app.route('/user/products/<category>/<productid>')
def user_product_details(category_name, product_id):
    return "Product Info"
# categories route
@token_required(role='user')
@app.route('/user/categories')
def user_categories():
    return "User categories page"




@app.route('/add-to-cart', methods=['POST'])
@token_required(role='user')
def add_to_cart():
    # print(getDataFromToken())
    user = getDataFromToken()
    
    user_id = user['USERID']   # adjust if your token stores differently
    product_id = request.form.get('product_id')

    # Get product details
    product = getProductById(product_id)

    if not product:
        flash("Product not found", "danger")
        return redirect(request.referrer)

    # Check if already in cart
    existing = getCartItem(user_id, product_id)

    if existing:
        increaseCartQuantity(user_id, product_id)
    else:
        insertCartItem(user_id, product_id, product['PRICE'])

    flash("Added to cart successfully", "success")
    return redirect(request.referrer)


@app.route('/cart')
@token_required(role='user')
def view_cart():
    user = getUserByToken()
    if not user:
        flash('Please login to view your cart.', 'warning')
        return redirect(url_for('login'))

    name = user.get('NAME', 'Dear User')
    user_id = user.get('USERID') or user.get('USER_ID') or user.get('user_id')

    cart_items = getUserCartItems(user_id)
    grand_total = sum(item['TOTAL_PRICE'] for item in cart_items)

    return render_template(
        'user/cart.html',
        cart_items=cart_items,
        grand_total=grand_total,
        user_logged_in=True,
        username=name
    )

@app.route('/remove-from-cart', methods=['POST'])
@token_required(role='user')
def remove_from_cart():
    user = getUserByToken()
    name = user.get('NAME','Dear User')
    user_id = user['USERID']
    product_id = request.form.get('product_id')

    # delete produt from cart
    removeFromCart(user_id=user_id, product_id=product_id)

    flash("Item removed from cart", "success")
    return redirect(url_for('view_cart'))

@app.route('/update-cart-quantity', methods=['POST'])
@token_required(role='user')
def update_cart_quantity():
    user_data = getDataFromToken()
    user_id = user_data['userid']
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')

    # update quantity
    updateCartQuantity(quantity=quantity, user_id=user_id, product_id=product_id)

    

    flash("Cart updated", "success")
    return redirect(url_for('view_cart'))


# users orders route
@token_required(role='user')
@app.route('/users/orders')
def user_orders():
    return "Users orders page"

# cart route
@app.route('/user/cart')
@token_required(role='user')
def user_cart():
    return redirect(url_for('view_cart'))


# -------------------place order related --------------------------
@app.route('/user/checkout')
@token_required(role='user')
def checkout():

    user = getUserByToken()   # from your token decorator
    name = user.get('NAME','Dear User')
    total_amount, cart_items = getCartItems(user['USERID'])

    return render_template(
        "user/checkout.html",
        cart_items=cart_items,
        total_amount=total_amount,
        username=name,
        user_logged_in=True

    )


@app.route('/user/place-order', methods=['POST'])
@token_required(role='user')
def place_order():

    user = getUserByToken()
    total_amount, cart_items = getCartItems(user['USERID'])

    fullname = request.form['fullname']
    phone = request.form['phone']
    address = request.form['address']
    city = request.form['city']
    pincode = request.form['pincode']
    payment_method = request.form.get('payment_method', 'COD').upper()

    if payment_method == 'RAZORPAY':
        payment_method = 'RAZORPAY'

    status, msg = placeOrder(user['USERID'], fullname, phone, address, city, pincode, total_amount, cart_items, payment_method)
    if not status:
        flash(message=msg)
        return redirect(url_for('view_cart'))

    msg = """
        🎉 Order Placed Successfully!
    """
    flash(msg)
    return redirect(url_for('user'))


@app.route('/user/create-razorpay-order', methods=['POST'])
@token_required(role='user')
def create_razorpay_order_route():
    user = getUserByToken()
    if not user:
        return jsonify({'error': 'User not authenticated'}), 401

    fullname = request.form.get('fullname')
    phone = request.form.get('phone')
    address = request.form.get('address')
    city = request.form.get('city')
    pincode = request.form.get('pincode')

    if not all([fullname, phone, address, city, pincode]):
        return jsonify({'error': 'Shipping information is required'}), 400

    total_amount, cart_items = getCartItems(user['USERID'])
    if not cart_items:
        return jsonify({'error': 'Your cart is empty'}), 400

    try:
        order_id = createPendingOrder(
            user_id=user['USERID'],
            fullname=fullname,
            phone=phone,
            address=address,
            city=city,
            pincode=pincode,
            total_amount=total_amount,
            cart_items=cart_items,
            payment_method='RAZORPAY'
        )

        payment_order = create_payment_order(
            amount=float(total_amount),
            receipt=str(order_id),
            notes={'user_id': str(user['USERID']), 'order_id': str(order_id)}
        )

        updateOrderPaymentStatus(
            order_id=order_id,
            payment_status='PENDING',
            razorpay_order_id=payment_order.get('id'),
            payment_method='RAZORPAY'
        )

        return jsonify({
            'order_id': order_id,
            'razorpay_order_id': payment_order.get('id'),
            'key': os.getenv('RAZORPAY_KEY_ID'),
            'amount': int(float(total_amount) * 100),
            'currency': 'INR',
            'name': 'Ecommerce',
            'description': 'Order Payment',
            'prefill': {
                'name': fullname,
                'contact': phone,
                'email': user.get('EMAIL') or ''
            }
        })
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/user/payment/verify', methods=['POST'])
@token_required(role='user')
def payment_verify():
    user = getUserByToken()
    payload = request.get_json(silent=True) or {}

    order_id = payload.get('order_id')
    razorpay_order_id = payload.get('razorpay_order_id')
    razorpay_payment_id = payload.get('razorpay_payment_id')
    razorpay_signature = payload.get('razorpay_signature')

    if not all([order_id, razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return jsonify({'error': 'Payment verification data is incomplete'}), 400

    order = getOrderById(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    if order['USER_ID'] != user['USERID']:
        return jsonify({'error': 'Order does not belong to this user'}), 403

    try:
        is_valid = verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature)
    except Exception as exc:
        markOrderPaymentFailure(order_id, str(exc))
        return jsonify({'error': str(exc)}), 400

    if not is_valid:
        markOrderPaymentFailure(order_id, 'Invalid Razorpay signature')
        return jsonify({'error': 'Invalid payment signature'}), 400

    total_amount, cart_items = getCartItems(user['USERID'])
    status, msg = finalizePaidOrder(order_id, user['USERID'], cart_items)
    if not status:
        updateOrderPaymentStatus(order_id, 'FAILED', razorpay_order_id, razorpay_payment_id, razorpay_signature, payment_method='RAZORPAY')
        return jsonify({'error': msg}), 400

    updateOrderPaymentStatus(
        order_id=order_id,
        payment_status='SUCCESS',
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
        payment_method='RAZORPAY'
    )

    return jsonify({'success': True, 'message': 'Payment verified and order completed.'})


@app.route('/user/payment/success')
@token_required(role='user')
def payment_success():
    order_id = request.args.get('order_id')
    return render_template('user/payment_success.html', order_id=order_id)


@app.route('/user/payment/failure')
@token_required(role='user')
def payment_failure():
    order_id = request.args.get('order_id')
    return render_template('user/payment_failure.html', order_id=order_id)


@app.route('/user/payment/cancelled')
@token_required(role='user')
def payment_cancelled():
    order_id = request.args.get('order_id')
    return render_template('user/payment_failure.html', order_id=order_id, cancelled=True)

# @app.route('/user/order-success')
# @token_required(role='user')
# def order_success():
#     return

@app.route('/my-orders')
@token_required(role='user')
def my_orders():
    user = getUserByToken()
    if not user:
        flash('Please login to view your orders.', 'warning')
        return redirect(url_for('login'))

    name = user.get('NAME', 'Dear User')
    orders = myOrders(user_id=user['USERID'])

    return render_template("user/my_orders.html", orders=orders, username=name, user_logged_in=True)




@app.route('/user/profile', methods=['GET', 'POST'])
@token_required(role='user')
def user_profile():
    user = getUserByToken()
    if not user:
        flash('Please login to view your profile.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name') or user.get('NAME')
        phone = request.form.get('phone') or user.get('PHONE_NUMBER')

        updateAdminProfile(
            userid=user['USERID'],
            name=name,
            phone=phone
        )

        flash("Profile updated successfully", "success")
        return redirect(url_for('user_profile'))

    return render_template(
        'user/profile.html',
        user=user,
        username=user.get('NAME'),
        user_email=user.get('EMAIL')
    )


@app.route('/user/change-password', methods=['POST'])
@token_required(role='user')
def user_change_password():
    user = getUserByToken()
    if not user:
        flash('Please login to update your password.', 'warning')
        return redirect(url_for('login'))

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')

    if not current_password or not new_password:
        flash('Current password and new password are required.', 'danger')
        return redirect(url_for('user_profile'))

    if not check_password_hash(user['PASSWORD'], current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('user_profile'))

    hashed_password = generate_password_hash(new_password)
    updateAdminProfile(user_id=user['USERID'], new_password=hashed_password)
    flash('Password updated successfully.', 'success')
    return redirect(url_for('user_profile'))

    return redirect(url_for('user_profile'))
@app.route('/user/logout')
def user_logout():
    response = make_response(redirect(url_for('login')))

    # delete token cookie
    response.set_cookie(
        'token',
        '',
        expires=0,
        httponly=True
    )

    return response

# main
if __name__ == "__main__":
    try:
        ensure_database_exists()
        createTables()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
        print("Make sure MySQL server is running and the database user has permission to create databases.")

    app.run(debug=True, port=5006)
    
    