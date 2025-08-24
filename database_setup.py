import psycopg2
from psycopg2 import sql

def setup_database():
    conn = psycopg2.connect(
        dbname="bar_management",
        user="postgres",
        password="Ruby1234",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()
    
    # Create tables with schema matching your existing products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            category VARCHAR(50) NOT NULL,
            product_name VARCHAR(255) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            current_stock INTEGER DEFAULT 0,
            icon VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id),
            quantity_sold INTEGER NOT NULL,
            sale_amount DECIMAL(10, 2) NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_updates (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id),
            previous_stock INTEGER NOT NULL,
            new_stock INTEGER NOT NULL,
            update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        );
    """)
    
    # Add missing columns to existing products table if they don't exist
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS current_stock INTEGER DEFAULT 0;")
        cursor.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS icon VARCHAR(10);")
    except Exception as e:
        print(f"Note: Some columns may already exist: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()

def update_stock_and_icons():
    """Update existing products with stock levels and icons"""
    conn = psycopg2.connect(
        dbname="bar_management",
        user="postgres",
        password="Ruby1234",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()
    
    # Update stock levels and add icons based on category
    category_icons = {
        'BOTTLES': '🍺',
        'CANS': '🥤', 
        'ENERGY DRINK': '⚡',
        'SOFT DRINKS': '🥤',
        'WINES': '🍷',
        'WHISKEY': '🥃',
        'GIN': '🍸',
        'VODKA': '🍸',
        'BRANDY': '🥃',
        'SPIRIT': '🥃',
        'TEQUILLA': '🍹',
        'COGNAC': '🥃',
        'RUM': '🥃',
        'LIQUER': '🍹',
        'ROOSTER': '🚬',
        'TOTS': '🥃',
        'SNACKS': '🍿'
    }
    
    # Set default stock levels (you can adjust these)
    default_stock = 10
    
    for category, icon in category_icons.items():
        cursor.execute("""
            UPDATE products 
            SET current_stock = %s, icon = %s 
            WHERE category = %s AND (current_stock IS NULL OR current_stock = 0);
        """, (default_stock, icon, category))
    
    conn.commit()
    cursor.close()
    conn.close()

def get_all_products():
    """Test function to retrieve and display all products"""
    conn = psycopg2.connect(
        dbname="bar_management",
        user="postgres",
        password="Ruby1234",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, category, product_name, price, current_stock, icon 
        FROM products 
        ORDER BY category, product_name;
    """)
    
    products = cursor.fetchall()
    
    print(f"\nFound {len(products)} products in database:")
    print("-" * 80)
    
    current_category = None
    for product in products:
        id, category, name, price, stock, icon = product
        
        if category != current_category:
            print(f"\n📦 {category}:")
            current_category = category
            
        print(f"  {icon or '📦'} {name} - KES {price} (Stock: {stock or 0})")
    
    cursor.close()
    conn.close()
    
    return products

def get_products_by_category(category):
    """Get products filtered by category"""
    conn = psycopg2.connect(
        dbname="bar_management",
        user="postgres",
        password="Ruby1234",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, category, product_name, price, current_stock, icon 
        FROM products 
        WHERE category = %s
        ORDER BY product_name;
    """, (category,))
    
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return products

def get_product_categories():
    """Get all unique categories"""
    conn = psycopg2.connect(
        dbname="bar_management",
        user="postgres",
        password="Ruby1234",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT category, COUNT(*) as product_count
        FROM products 
        GROUP BY category
        ORDER BY category;
    """)
    
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return categories

if __name__ == "__main__":
    print("Setting up database...")
    setup_database()
    
    print("Updating stock levels and icons...")
    update_stock_and_icons()
    
    print("Testing database connection...")
    products = get_all_products()
    
    print(f"\n✅ Database setup complete! {len(products)} products loaded.")
    
    # Show categories summary
    categories = get_product_categories()
    print(f"\n📊 Categories Summary:")
    for cat, count in categories:
        print(f"  • {cat}: {count} products")