"""Small, repeatable starter catalog for a fresh/demo installation."""

from database.connection import databaseConfig


DEMO_PRODUCTS = [
    ("Everyday Wireless Headphones", "Comfort fit wireless headphones with clear calls, deep sound and up to 30 hours of battery life.", "Electronics", 2499.00, 32, "images/products/headphones.svg"),
    ("Smartphone 128 GB", "Bright 6.5-inch display, all-day battery and 128 GB of storage for everyday use.", "Electronics", 18999.00, 18, "images/products/phone.svg"),
    ("Classic Canvas Backpack", "A sturdy 20-litre day pack with padded straps, a laptop sleeve and water-resistant canvas.", "Clothing", 1599.00, 26, "images/products/backpack.svg"),
    ("Everyday Knit Sneakers", "Lightweight cushioned sneakers with a breathable knit upper for daily walks and commutes.", "Clothing", 2199.00, 21, "images/products/sneakers.svg"),
    ("Compact Air Fryer", "A 4-litre air fryer with adjustable temperature and a removable non-stick basket.", "Home & Kitchen", 4999.00, 12, "images/products/air-fryer.svg"),
    ("Ceramic Table Lamp", "Warm, dimmable bedside lighting with a linen shade and a matte ceramic base.", "Home & Kitchen", 1799.00, 15, "images/products/lamp.svg"),
    ("Adjustable Dumbbell Pair", "Space-saving adjustable dumbbells for strength training at home. Pair, 2–10 kg each.", "Sports & Outdoors", 3499.00, 9, "images/products/dumbbells.svg"),
    ("Trail Daypack 18 L", "A lightweight hiking pack with a breathable back panel, bottle pockets and rain cover.", "Sports & Outdoors", 2799.00, 14, "images/products/trail-pack.svg"),
]


def seed_demo_catalog():
    """Insert missing demo products without replacing any store data."""
    db = databaseConfig()
    cursor = db.cursor()
    try:
        for name, description, category, price, stock, image in DEMO_PRODUCTS:
            cursor.execute("SELECT PRODUCTID FROM PRODUCTS WHERE NAME = %s LIMIT 1", (name,))
            if cursor.fetchone():
                continue
            cursor.execute(
                """INSERT INTO PRODUCTS
                   (NAME, DESCRIPTION, CATEGORY, PRICE, STOCK, ACTIVE, IMAGE_URL)
                   VALUES (%s, %s, %s, %s, %s, 1, %s)""",
                (name, description, category, price, stock, image),
            )
        db.commit()
    finally:
        cursor.close()
        db.close()
