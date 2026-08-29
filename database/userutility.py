from database.connection import databaseConfig

# get products based on category
def getProductsByCategory(category_name, min_price, max_price,sort):
    # database accesss
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)
    query = "SELECT * FROM PRODUCTS WHERE category=%s AND ACTIVE=1"
    params = [category_name]

    # Price filter
    if min_price:
        query += " AND PRICE >= %s"
        params.append(min_price)

    if max_price:
        query += " AND PRICE <= %s"
        params.append(max_price)

    # Sorting
    if sort == "low":
        query += " ORDER BY PRICE ASC"
    elif sort == "high":
        query += " ORDER BY PRICE DESC"
    else:
        query += " ORDER BY PRODUCTID DESC"

    cursor.execute(query, tuple(params))
    products = cursor.fetchall()
    cursor.close()
    db_config.close()
    return products


# 
def getProductById(productid:int):
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)
    cursor.execute("SELECT * FROM PRODUCTS WHERE PRODUCTID=%s;", (productid,))
    product = cursor.fetchone()
    cursor.close()
    db_config.close()
    return product

def getCartItem(user_id, product_id):
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)

    query = """
        SELECT * FROM CART
        WHERE USER_ID = %s AND PRODUCTID = %s;
    """

    cursor.execute(query, (user_id, product_id))
    result = cursor.fetchone()

    cursor.close()
    db_config.close()

    return result

# iuncreate cart quantity
def increaseCartQuantity(user_id, product_id):
    db_config = databaseConfig()
    cursor = db_config.cursor()

    query = """
        UPDATE CART
        SET QUANTITY = QUANTITY + 1,
            UPDATED_AT = CURRENT_TIMESTAMP
        WHERE USER_ID = %s AND PRODUCTID = %s;
    """

    cursor.execute(query, (user_id, product_id))
    db_config.commit()

    cursor.close()
    db_config.close()

# insert product into cart
def insertCartItem(user_id, product_id, price):
    db_config = databaseConfig()
    cursor = db_config.cursor()

    query = """
        INSERT INTO CART (USER_ID, PRODUCTID, QUANTITY, PRICE)
        VALUES (%s, %s, 1, %s);
    """

    cursor.execute(query, (user_id, product_id, price))
    db_config.commit()

    cursor.close()
    db_config.close()



def getUserCartItems(user_id):
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)

    query = """
        SELECT 
            C.CARTID,
            C.PRODUCTID,
            P.NAME,
            P.IMAGE_URL,
            C.QUANTITY,
            C.PRICE,
            (C.QUANTITY * C.PRICE) AS TOTAL_PRICE
        FROM CART C
        JOIN PRODUCTS P ON C.PRODUCTID = P.PRODUCTID
        WHERE C.USER_ID = %s;
    """

    cursor.execute(query, (user_id,))
    results = cursor.fetchall()

    cursor.close()
    db_config.close()

    return results

# delete cart 
def removeFromCart(user_id:int, product_id:int):
    db_config = databaseConfig()
    cursor = db_config.cursor()

    query = """
        DELETE FROM CART
        WHERE USER_ID = %s AND PRODUCTID = %s;
    """

    cursor.execute(query, (user_id, product_id))
    db_config.commit()

    cursor.close()
    db_config.close()


def updateCartQuantity(quantity:int, user_id:int, product_id:int):

    db_config = databaseConfig()
    cursor = db_config.cursor()

    query = """
        UPDATE CART
        SET QUANTITY = %s,
            UPDATED_AT = CURRENT_TIMESTAMP
        WHERE USER_ID = %s AND PRODUCTID = %s;
    """

    cursor.execute(query, (quantity, user_id, product_id))
    db_config.commit()
    cursor.close()
    db_config.close()


# get products based on search
def getProductsBasedOnSearch(product_name:str):
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)

    query = """select * from products where name like %s;"""

    cursor.execute(query, (f"%{product_name}%",))
    products = cursor.fetchall()
    cursor.close()
    db_config.close()
    return products


# 
def getCartItems(user_id):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT p.NAME,
                p.PRODUCTID,
               p.PRICE,
               c.QUANTITY,
               (p.PRICE * c.QUANTITY) AS TOTAL
        FROM CART c
        JOIN PRODUCTS p ON c.PRODUCTID = p.PRODUCTID
        WHERE c.USER_ID = %s
    """

    cursor.execute(query, (user_id,))
    cart_items = cursor.fetchall()

    total_amount = sum(item["TOTAL"] for item in cart_items)

    cursor.close()
    db.close()
    return total_amount, cart_items


def createPendingOrder(user_id, fullname, phone, address, city, pincode, total_amount, cart_items, payment_method='COD'):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        INSERT INTO ORDERS (
            USER_ID, FULLNAME, PHONE, ADDRESS, CITY, PINCODE, TOTAL_AMOUNT,
            PAYMENT_METHOD, PAYMENT_STATUS, ORDERSTATUS
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', 'PENDING')
    """, (user_id, fullname, phone, address, city, pincode, total_amount, payment_method))

    order_id = cursor.lastrowid

    for item in cart_items:
        cursor.execute("""
            INSERT INTO ORDER_ITEMS
            (ORDERID, PRODUCTID, PRODUCTNAME, PRODUCTPRICE, QUANTITY)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            order_id,
            item["PRODUCTID"],
            item["NAME"],
            item["PRICE"],
            item["QUANTITY"]
        ))

    db.commit()
    cursor.close()
    db.close()
    return order_id


def finalizePaidOrder(order_id, user_id, cart_items):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    for item in cart_items:
        cursor.execute("SELECT STOCK FROM products WHERE PRODUCTID = %s", (item["PRODUCTID"],))
        current_quantity = cursor.fetchone()['STOCK']
        if current_quantity >= item["QUANTITY"]:
            cursor.execute('UPDATE products SET STOCK = STOCK - %s WHERE PRODUCTID = %s', (item["QUANTITY"], item["PRODUCTID"]))
        else:
            cursor.close()
            db.close()
            return False, f"{item['NAME']} available quantity is {current_quantity}"

    cursor.execute("UPDATE ORDERS SET PAYMENT_STATUS = 'SUCCESS', ORDERSTATUS = 'PAID' WHERE ORDERID = %s", (order_id,))
    cursor.execute("DELETE FROM CART WHERE USER_ID = %s", (user_id,))
    db.commit()
    cursor.close()
    db.close()
    return True, "Success"


def placeOrder(user_id, fullname, phone, address, city, pincode, total_amount, cart_items, payment_method='COD'):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        INSERT INTO ORDERS (USER_ID, FULLNAME, PHONE, ADDRESS, CITY, PINCODE, TOTAL_AMOUNT, PAYMENT_METHOD, PAYMENT_STATUS, ORDERSTATUS)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'SUCCESS', 'PAID')
    """, (user_id, fullname, phone, address, city, pincode, total_amount, payment_method))

    order_id = cursor.lastrowid

    for item in cart_items:
        cursor.execute("""
            INSERT INTO ORDER_ITEMS
            (ORDERID, PRODUCTID, PRODUCTNAME, PRODUCTPRICE, QUANTITY)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            order_id,
            item["PRODUCTID"],
            item["NAME"],
            item["PRICE"],
            item["QUANTITY"]
        ))

    cursor.execute("DELETE FROM CART WHERE USER_ID=%s", (user_id,))
    for item in cart_items:
        cursor.execute("SELECT STOCK FROM products WHERE PRODUCTID = %s", (item["PRODUCTID"],))
        current_quantity = cursor.fetchone()['STOCK']
        if current_quantity >= item["QUANTITY"]:
            cursor.execute('UPDATE products SET STOCK = STOCK - %s WHERE PRODUCTID = %s', (item["QUANTITY"], item["PRODUCTID"]))
        else:
            cursor.close()
            db.close()
            return False, f"{item['NAME']} avalilabe quantity is {current_quantity}"

    db.commit()
    cursor.close()
    db.close()
    return True, "Success"



# my orders 
def myOrders(user_id):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)
    

    cursor.execute("""
        SELECT * FROM ORDERS
        WHERE USER_ID = %s
        ORDER BY CREATED_AT DESC
    """, (user_id,))

    orders = cursor.fetchall()
    cursor.close()
    return orders