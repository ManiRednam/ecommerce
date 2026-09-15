from database.connection import databaseConfig


def normalize_user_row(row):
    if not row:
        return row

    normalized = dict(row)

    user_id = (
        normalized.get('user_id')
        or normalized.get('USER_ID')
        or normalized.get('USERID')
        or normalized.get('userid')
    )
    if user_id is not None:
        normalized['user_id'] = user_id
        normalized['USER_ID'] = user_id
        normalized['USERID'] = user_id
        normalized['userid'] = user_id

    name = normalized.get('name') or normalized.get('NAME')
    if name is not None:
        normalized['name'] = name
        normalized['NAME'] = name

    email = normalized.get('email') or normalized.get('EMAIL')
    if email is not None:
        normalized['email'] = email
        normalized['EMAIL'] = email

    phone = normalized.get('phone_number') or normalized.get('PHONE_NUMBER') or normalized.get('phone')
    if phone is not None:
        normalized['phone_number'] = phone
        normalized['PHONE_NUMBER'] = phone
        normalized['phone'] = phone

    password = normalized.get('password') or normalized.get('PASSWORD')
    if password is not None:
        normalized['password'] = password
        normalized['PASSWORD'] = password

    role = normalized.get('role') or normalized.get('ROLE')
    if role is not None:
        normalized['role'] = role
        normalized['ROLE'] = role

    profile_image = normalized.get('profile_image') or normalized.get('PROFILE_IMAGE')
    if profile_image is not None:
        normalized['profile_image'] = profile_image
        normalized['PROFILE_IMAGE'] = profile_image

    return normalized


# check user exists or not
def checkUserExists(email:str):
    # database accesss
    db_config = databaseConfig()
    cursor = db_config.cursor()
    cursor.execute('select user_id from users where email=%s;', (email,))
    
    if cursor.fetchone():
        cursor.close()
        db_config.close()
        return True
    else:
        cursor.close()
        db_config.close()
        return False
    
# insert user data into db
def addUser(name: str, email: str, phone_number: str, password: str, profile_image: str = None):
    db = databaseConfig()
    cursor = db.cursor()

    query = """
        INSERT INTO users
        (NAME, EMAIL, PHONE_NUMBER, PASSWORD, PROFILE_IMAGE)
        VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute(query, (name, email, phone_number, password, profile_image))
    db.commit()
    cursor.close()
    db.close()

    

# get password and role form database
def getUserDetails(email:str, role:str=None):
    # database accesss
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)
    user_details_query = "select user_id,name, password, role from users where email = %s;"
    if role:
        user_details_query =  "select user_id, password, role from users where email = %s and role = %s"
        cursor.execute(user_details_query, (email,role))
    else:
        cursor.execute(user_details_query, (email,))
    data = cursor.fetchone()
    cursor.close()
    db_config.close()
    return normalize_user_row(data)

# get user details by id
def getUserDetailsByID(user_id:int, role:str=None):
    # database accesss
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)
    user_details_query = "select * from users where user_id = %s;"
    
    cursor.execute(user_details_query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    db_config.close()
    return normalize_user_row(user)


def getOrderById(order_id:int):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ORDERS WHERE ORDERID = %s", (order_id,))
    order = cursor.fetchone()
    cursor.close()
    db.close()
    return order


def getOrderItemsByOrderId(order_id:int):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM ORDER_ITEMS WHERE ORDERID = %s ORDER BY ID ASC",
        (order_id,)
    )
    items = cursor.fetchall()
    cursor.close()
    db.close()
    return items


## Get all categories from database
def getCatagoriesFromDB():
    db_config = databaseConfig()
    cursor = db_config.cursor()
    cursor.execute('select distinct(category) from products;')
    category_list = cursor.fetchall()
    for i in range(len(category_list)):
        category_list[i] = category_list[i][0]
    cursor.close()
    db_config.close()
    return category_list


## Get all products from database
def getProductsFromDB(name='', category='', status=''):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)
    query = "SELECT * FROM products WHERE 1=1"
    values = []
    # Filter by product name
    if name:
        query += " AND NAME LIKE %s" # "SELECT * FROM products WHERE 1=1 AND NAME LIKE %s"
        values.append(f"%{name}%")
    # Filter by category
    if category:
        
        query += " AND CATEGORY = %s"
        values.append(category)
        
    # Filter by status
    if status:
        query += " AND ACTIVE = %s"
        values.append(status)
    cursor.execute(query, values)
    products = cursor.fetchall()
    # print(products[:5])
    cursor.close()
    db.close()
    return products




def addProductToDB(name, description, category, price, stock, active, image_url):
    db = databaseConfig()
    cursor = db.cursor()

    product_insert_query = """
        INSERT INTO products
        (NAME, DEScrIPTION, CATEGORY, PRICE, STOCK, ACTIVE, IMAGE_URL)
        VALUES (%s,%s,%s,%s,%s,%s, %s)
    """

    cursor.execute(product_insert_query, (name, description, category,price, stock, active, image_url))

    db.commit()
    cursor.close()
    db.close()


## Total Orders
def totalOrdersCount(status:str=None):
    db = databaseConfig()
    cursor = db.cursor()
    if status:
        cursor.execute("SELECT COUNT(*) FROM ORDERS where ORDERSTATUS not like %s;", ("DELIVERED",))
        
    else:
        cursor.execute("SELECT COUNT(*) FROM ORDERS;")
    orders_count = cursor.fetchone()[0]
    cursor.close()
    db.close()
    return orders_count

# get orders 
def getOrders(orderid="", product_name="", from_date="", to_date=""):

    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT 
            o.ORDERID AS ORDER_ID,
            o.USER_ID AS USER_ID,
            o.CREATED_AT,
            o.ORDERSTATUS AS ORDER_STATUS,

            oi.PRODUCTNAME AS PRODUCT_NAME,
            oi.TOTALPRICE AS TOTAL_PRICE

        FROM ORDERS o
        JOIN ORDER_ITEMS oi ON o.ORDERID = oi.ORDERID
        WHERE 1=1
    """

    params = []

    # 🔍 Filter by Order ID
    if orderid:
        query += " AND o.ORDERID = %s"
        params.append(orderid)

    # 🔍 Filter by Product Name
    if product_name:
        query += " AND oi.PRODUCTNAME LIKE %s"
        params.append(f"%{product_name}%")

    # 🔍 Filter by Date Range
    if from_date:
        query += " AND DATE(o.CREATED_AT) >= %s"
        params.append(from_date)

    if to_date:
        query += " AND DATE(o.CREATED_AT) <= %s"
        params.append(to_date)

    query += " ORDER BY o.CREATED_AT DESC"

    cursor.execute(query, tuple(params))
    orders = cursor.fetchall()

    cursor.close()
    db.close()

    return orders


def toggleProduct(pid, status):
    db = databaseConfig()
    cursor = db.cursor()

    cursor.execute(
        "UPDATE products SET ACTIVE=%s WHERE PRODUCTID=%s",
        (status, pid)
    )

    db.commit()
    cursor.close()
    db.close()


# get users info 
def usersDetails(name:str="", email:str="",role:str=''):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    query = "SELECT USER_ID, NAME, EMAIL, PHONE_NUMBER, ROLE, CREATED_AT, PROFILE_IMAGE FROM USERS WHERE 1=1"
    values = []

    if name:
        query += " AND NAME LIKE %s"
        values.append(f"%{name}%")

    if email:
        query += " AND EMAIL LIKE %s"
        values.append(f"%{email}%")

    if role:
        query += " AND ROLE = %s"
        values.append(role)

    query += " ORDER BY CREATED_AT DESC"

    cursor.execute(query, values)
    users = cursor.fetchall()

    cursor.close()
    db.close()
    return users


# update admin/user profile in database
def updateAdminProfile(user_id:int=None, new_password:str=None, name:str=None, phone:str=None, email:str=None):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    fields = []
    values = []

    if new_password is not None:
        fields.append("PASSWORD = %s")
        values.append(new_password)

    if name is not None:
        fields.append("NAME = %s")
        values.append(name)

    if phone is not None:
        fields.append("PHONE_NUMBER = %s")
        values.append(phone)

    if email is not None:
        fields.append("EMAIL = %s")
        values.append(email)

    if not fields or user_id is None:
        cursor.close()
        db.close()
        return False

    values.append(user_id)
    query = f"UPDATE USERS SET {', '.join(fields)} WHERE USER_ID = %s"
    cursor.execute(query, tuple(values))
    db.commit()
    cursor.close()
    db.close()
    return True



# get product details bt id
def getProductDetailsByID(productid:int):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    # FETCH PRODUCT
    cursor.execute(
        "SELECT * FROM products WHERE PRODUCTID = %s",
        (productid,)
    )
    product = cursor.fetchone()
    return product

# update product info in database
def updateProductInfo(name, description, category,price, stock, active, productid):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)
    update_query = """
            UPDATE products SET NAME=%s, DESCRIPTION=%s, CATEGORY=%s, PRICE=%s, STOCK=%s, ACTIVE=%s
            WHERE PRODUCTID=%s;
        """

    cursor.execute(update_query, (name, description, category,price, stock, active, productid))
    db.commit()
    return True

## Deactivate product in database
def updateProductStatus(productid, status:int=0):
    db = databaseConfig()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE products SET ACTIVE = %s WHERE PRODUCTID = %s",
        (status, productid)
    )
    db.commit()
    cursor.close()
    db.close()
    return True



## get view user
def viewUserByAdmin(user_id):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT USER_ID, NAME, EMAIL, ROLE, STATUS, CREATED_AT "
        "FROM users WHERE USER_ID = %s",
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.close()
    db.close()
    return user


def markOrderPaymentFailure(order_id:int, reason:str=None):
    db = databaseConfig()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE ORDERS SET PAYMENT_STATUS = 'FAILED', ORDERSTATUS = 'FAILED', PAYMENT_FAILURE_REASON = %s WHERE ORDERID = %s",
        (reason, order_id)
    )
    db.commit()
    cursor.close()
    db.close()


def updateOrderPaymentStatus(order_id:int, payment_status:str, razorpay_order_id:str=None, razorpay_payment_id:str=None,
                            razorpay_signature:str=None, payment_id:str=None, payment_method:str='RAZORPAY'):
    db = databaseConfig()
    cursor = db.cursor()
    query = """
        UPDATE ORDERS
        SET PAYMENT_STATUS = %s,
            PAYMENT_METHOD = %s,
            RAZORPAY_ORDER_ID = COALESCE(%s, RAZORPAY_ORDER_ID),
            RAZORPAY_PAYMENT_ID = COALESCE(%s, RAZORPAY_PAYMENT_ID),
            RAZORPAY_SIGNATURE = COALESCE(%s, RAZORPAY_SIGNATURE),
            PAYMENT_ID = COALESCE(%s, PAYMENT_ID)
        WHERE ORDERID = %s
    """
    cursor.execute(query, (payment_status, payment_method, razorpay_order_id, razorpay_payment_id, razorpay_signature, payment_id, order_id))
    db.commit()
    cursor.close()
    db.close()


# view order
def viewOrderDetails(order_id):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    #  Get Order Main Details
    cursor.execute("""
        SELECT *
        FROM ORDERS
        WHERE ORDERID = %s
    """, (order_id,))

    order = cursor.fetchone()

    if not order:
        cursor.close()
        db.close()
        return "Order not found"

    #  Get Order Items
    cursor.execute("""
        SELECT PRODUCTNAME,
               PRODUCTPRICE,
               QUANTITY,
               TOTALPRICE
        FROM ORDER_ITEMS
        WHERE ORDERID = %s
    """, (order_id,))

    items = cursor.fetchall()

    cursor.close()
    db.close()
    return order, items

def totalProducts():
    db = databaseConfig()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM PRODUCTS;")
    return cursor.fetchone()[0]