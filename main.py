from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
try:
    from report_generator import generate_report
except Exception as e:
    print(f"Report generator not available: {e}")
    def generate_report(*args, **kwargs):
        raise ImportError("report_generator or its dependencies are not available")
import os
from datetime import datetime
import psycopg2
from psycopg2 import sql, OperationalError
from dotenv import load_dotenv
import sys
from kivy.uix.label import Label
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout

# Load environment variables
load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        """Establish database connection with multiple fallback methods"""
        connection_params = [
            # Primary connection parameters
            {
                'dbname': os.getenv('DB_NAME', 'bar_management'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'Ruby1234'),
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'connect_timeout': 5
            },
            # Unix socket connection
            {
                'dbname': 'bar_management',
                'user': 'postgres',
                'host': '/var/run/postgresql'
            },
            # Peer authentication
            {
                'dbname': 'bar_management',
                'user': 'postgres',
                'host': 'localhost'
            }
        ]

        for params in connection_params:
            try:
                self.conn = psycopg2.connect(**params)
                print(f"✅ Database connection established with params: {params}")
                self.initialize_database()
                return
            except OperationalError as e:
                print(f"❌ Connection attempt failed with params {params}: {e}")
        
        raise ConnectionError("Could not establish database connection after multiple attempts")

    def initialize_database(self):
        """Create tables if they don't exist"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS products (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        category VARCHAR(100) NOT NULL,
                        subcategory VARCHAR(100),
                        current_stock INTEGER NOT NULL,
                        price DECIMAL(10, 2) NOT NULL,
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
                
                self.conn.commit()
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise

    def get_products(self, category="All", subcategory="All"):
        """Retrieve products with optional filtering"""
        with self.conn.cursor() as cursor:
            query = "SELECT name, current_stock, price, category, subcategory, icon FROM products"
            params = []
            
            if category != "All":
                query += " WHERE category = %s"
                params.append(category)
                if subcategory != "All":
                    query += " AND subcategory = %s"
                    params.append(subcategory)
            
            query += " ORDER BY category, subcategory, name"
            cursor.execute(query, params)
            
            return [{
                "name": p[0],
                "stock": p[1],
                "price": float(p[2]),
                "category": p[3],
                "subcategory": p[4],
                "icon": p[5] if p[5] else "📦"
            } for p in cursor.fetchall()]

    def get_categories(self):
        """Get all distinct product categories"""
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
            return ["All"] + [row[0] for row in cursor.fetchall()]

    def get_subcategories(self, category):
        """Get subcategories for a specific category"""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT subcategory FROM products 
                WHERE category = %s AND subcategory IS NOT NULL 
                ORDER BY subcategory
            """, (category,))
            return ["All"] + [row[0] for row in cursor.fetchall()]

    def update_stock(self, product_name, quantity_sold):
        """Update product stock after sale"""
        with self.conn.cursor() as cursor:
            try:
                # Get current stock
                cursor.execute("""
                    SELECT id, current_stock FROM products WHERE name = %s
                    FOR UPDATE
                """, (product_name,))
                product = cursor.fetchone()
                
                if not product:
                    return False
                
                product_id, current_stock = product
                new_stock = current_stock - quantity_sold
                
                # Update product stock
                cursor.execute("""
                    UPDATE products 
                    SET current_stock = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (new_stock, product_id))
                
                # Record the sale
                sale_amount = quantity_sold * self.get_product_price(product_name)
                cursor.execute("""
                    INSERT INTO sales (product_id, quantity_sold, sale_amount)
                    VALUES (%s, %s, %s)
                """, (product_id, quantity_sold, sale_amount))
                
                # Record stock update
                cursor.execute("""
                    INSERT INTO stock_updates 
                    (product_id, previous_stock, new_stock, notes)
                    VALUES (%s, %s, %s, %s)
                """, (product_id, current_stock, new_stock, f"Sold {quantity_sold} items"))
                
                self.conn.commit()
                return True
            except Exception as e:
                self.conn.rollback()
                print(f"Error updating stock: {e}")
                return False

    def get_product_price(self, product_name):
        """Get price for a specific product"""
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT price FROM products WHERE name = %s", (product_name,))
            result = cursor.fetchone()
            return float(result[0]) if result else 0.0

    def add_new_product(self, product_data):
        """Add a new product to the database"""
        with self.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    INSERT INTO products 
                    (name, category, subcategory, current_stock, price, icon)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, (
                    product_data["name"],
                    product_data["category"],
                    product_data.get("subcategory"),
                    product_data["stock"],
                    product_data["price"],
                    product_data.get("icon", "📦")
                ))
                self.conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                self.conn.rollback()
                print(f"Error adding product: {e}")
                return False

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

class ProductRow(BoxLayout):
    product_name = StringProperty("")
    stock = NumericProperty(0)
    price = NumericProperty(0)
    category = StringProperty("")
    subcategory = StringProperty("")
    icon = StringProperty("")
    
    def increment_quantity(self):
        try:
            current = int(self.ids.qty_input.text) if self.ids.qty_input.text else 0
            if current < self.stock:
                self.ids.qty_input.text = str(current + 1)
                self.update_parent_preview()
        except (ValueError, AttributeError):
            self.ids.qty_input.text = "0"
    
    def decrement_quantity(self):
        try:
            current = int(self.ids.qty_input.text) if self.ids.qty_input.text else 0
            self.ids.qty_input.text = str(max(0, current - 1))
            self.update_parent_preview()
        except (ValueError, AttributeError):
            self.ids.qty_input.text = "0"
    
    def update_parent_preview(self):
        root = self.get_root_widget()
        if hasattr(root, 'calculate_preview'):
            root.calculate_preview()
    
    def get_root_widget(self):
        widget = self
        while widget.parent:
            if isinstance(widget, SalesForm):
                return widget
            widget = widget.parent
        return None

class AddProductForm(BoxLayout):
    db = ObjectProperty(None)
    
    def add_product(self):
        name = self.ids.product_name.text.strip()
        category = self.ids.product_category.text.strip()
        subcategory = self.ids.product_subcategory.text.strip()
        stock = self.ids.product_stock.text.strip()
        price = self.ids.product_price.text.strip()
        
        if not all([name, category, stock, price]):
            self.ids.status.text = "❌ Please fill all required fields"
            self.ids.status.color = (0.9, 0.2, 0.2, 1)
            return
        
        try:
            stock = int(stock)
            price = float(price)
        except ValueError:
            self.ids.status.text = "❌ Stock must be integer and price must be number"
            self.ids.status.color = (0.9, 0.2, 0.2, 1)
            return
        
        product_data = {
            "name": name,
            "category": category,
            "subcategory": subcategory if subcategory else None,
            "stock": stock,
            "price": price
        }
        
        if self.db.add_new_product(product_data):
            self.ids.status.text = "✅ Product added successfully!"
            self.ids.status.color = (0.2, 0.8, 0.2, 1)
            self.clear_form()
        else:
            self.ids.status.text = "❌ Error adding product (may already exist)"
            self.ids.status.color = (0.9, 0.2, 0.2, 1)
    
    def clear_form(self):
        self.ids.product_name.text = ""
        self.ids.product_category.text = ""
        self.ids.product_subcategory.text = ""
        self.ids.product_stock.text = ""
        self.ids.product_price.text = ""

class SalesForm(BoxLayout):
    categories = ListProperty(["All"])
    subcategories = ListProperty(["All"])
    db = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_category = "All"
        self.current_subcategory = "All"
        self.initialized = False
        
        # Initialize database connection
        try:
            self.db = DatabaseManager()
            self.categories = self.db.get_categories()
            self.subcategories = ["All"]
            Clock.schedule_once(self._delayed_init, 0.1)
        except Exception as e:
            print(f"Database initialization failed: {e}")
            # Fallback to mock data
            self.products_data = [
                {"name": "Beer", "category": "Beer", "subcategory": "Local", "stock": 50, "price": 200, "icon": "🍺"},
                {"name": "Whiskey", "category": "Whiskey", "subcategory": "Imported", "stock": 20, "price": 1000, "icon": "🥃"},
                {"name": "Vodka", "category": "Vodka", "subcategory": "Imported", "stock": 30, "price": 800, "icon": "🍸"},
            ]
            self.categories = ["All", "Beer", "Whiskey", "Vodka"]
            self.subcategories = ["All", "Local", "Imported"]
            Clock.schedule_once(self.populate_products, 0.1)

    def _delayed_init(self, dt):
        if not self.initialized:
            self.apply_filters()
            self.initialized = True
    
    def update_subcategories(self, category):
        if category == "All":
            self.subcategories = ["All"]
        else:
            if self.db:
                self.subcategories = self.db.get_subcategories(category)
            else:
                # Mock subcategories for fallback
                if category == "Beer":
                    self.subcategories = ["All", "Local", "Imported", "Craft"]
                elif category == "Whiskey":
                    self.subcategories = ["All", "Scotch", "Bourbon", "Irish"]
                elif category == "Vodka":
                    self.subcategories = ["All", "Regular", "Premium", "Flavored"]
                else:
                    self.subcategories = ["All"]
        
        if hasattr(self.ids, 'subcategory_filter'):
            self.ids.subcategory_filter.values = self.subcategories
            self.ids.subcategory_filter.text = "All"
    
    def filter_by_category(self, category):
        self.current_category = category
        self.update_subcategories(category)
        self.apply_filters()
    
    def filter_by_subcategory(self, subcategory):
        self.current_subcategory = subcategory
        self.apply_filters()
    
    def apply_filters(self):
        if self.db:
            self.products_data = self.db.get_products(
                category=self.current_category if self.current_category != "All" else "All",
                subcategory=self.current_subcategory if self.current_subcategory != "All" else "All"
            )
        # If no db, products_data is already set in __init__
        self.populate_products()
    
    def populate_products(self, dt=None):
        if not hasattr(self, 'ids') or not hasattr(self.ids, 'products_grid'):
            Clock.schedule_once(self.populate_products, 0.1)
            return
            
        grid = self.ids.products_grid
        grid.clear_widgets()
        
        for item in self.products_data:
            row = ProductRow(
                product_name=item["name"],
                stock=item["stock"],
                price=item["price"],
                category=item["category"],
                subcategory=item.get("subcategory", ""),
                icon=item.get("icon", "📦")
            )
            grid.add_widget(row)
        
        Clock.schedule_once(lambda dt: self.calculate_preview(), 0.1)

    def calculate_preview(self):
        if not hasattr(self, 'ids') or not hasattr(self.ids, 'products_grid'):
            return
            
        total_revenue = 0
        total_items = 0
        
        try:
            for row in self.ids.products_grid.children:
                if hasattr(row, 'ids') and hasattr(row.ids, 'qty_input'):
                    qty_text = row.ids.qty_input.text
                    if qty_text and qty_text.isdigit():
                        qty_sold = int(qty_text)
                        total_revenue += qty_sold * row.price
                        total_items += qty_sold
        except (ValueError, AttributeError) as e:
            print(f"Error calculating preview: {e}")
            
        self.total_revenue = total_revenue
        self.total_items_sold = total_items
        
        if hasattr(self.ids, 'revenue_preview'):
            self.ids.revenue_preview.text = f"Ksh {total_revenue:,}"
        if hasattr(self.ids, 'items_preview'):
            self.ids.items_preview.text = f"{total_items} items"

    def generate_report(self):
        try:
            data = []
            total_sales = 0
            has_sales = False
            
            for row in self.ids.products_grid.children:
                qty_sold = 0
                if hasattr(row, 'ids') and hasattr(row.ids, 'qty_input'):
                    qty_text = row.ids.qty_input.text
                    if qty_text and qty_text.isdigit():
                        qty_sold = int(qty_text)
                
                if qty_sold == 0:
                    continue
                    
                has_sales = True
                
                if qty_sold > row.stock:
                    self.show_error(f"❌ {row.product_name}: Quantity ({qty_sold}) exceeds available stock ({row.stock})")
                    return
                
                sale_amount = qty_sold * row.price
                total_sales += sale_amount
                
                data.append({
                    "Product Name": row.product_name,
                    "Category": row.category,
                    "Subcategory": row.subcategory,
                    "Stock Before": row.stock,
                    "Quantity Sold": qty_sold,
                    "Price Per Unit": row.price,
                    "Total Sale": sale_amount,
                    "Stock After": row.stock - qty_sold
                })
                
                # Only update stock if we have a database connection
                if self.db and not self.db.update_stock(row.product_name, qty_sold):
                    self.show_error(f"❌ Failed to update stock for {row.product_name}")
                    return
            
            if not has_sales:
                self.show_error("❌ No sales data entered. Please add quantities for products sold.")
                return

            expenditure_text = self.ids.expenditure.text
            expenditure = 0
            if expenditure_text:
                try:
                    expenditure = float(expenditure_text)
                    if expenditure < 0:
                        self.show_error("❌ Expenditure cannot be negative")
                        return
                except ValueError:
                    self.show_error("❌ Please enter a valid expenditure amount")
                    return
                
            report_path = generate_report(data, expenditure)

            config_tax_rate = 0.16  # Default tax rate
            try:
                import json
                with open("bar_config.json", 'r') as f:
                    config = json.load(f)
                    config_tax_rate = config.get('tax_rate', 0.16)
            except:
                pass
                
            tax_amount = total_sales * config_tax_rate
            net_profit = total_sales - expenditure - tax_amount
            profit_status = "Profit" if net_profit >= 0 else "Loss"
            
            self.show_success(
                f"✅ Report generated successfully!\n"
                f"📁 File: {os.path.basename(report_path)}\n"
                f"💰 Gross Sales: Ksh {total_sales:,}\n"
                f"💳 Expenditure: Ksh {expenditure:,}\n"
                f"🏛️ Tax (VAT): Ksh {tax_amount:,.2f}\n"
                f"📊 Net {profit_status}: Ksh {abs(net_profit):,.2f}"
            )
            
            self.clear_inputs_only()
            self.apply_filters()  # Refresh to get updated stock levels

        except ImportError:
            self.show_error("❌ Error: report_generator.py not found. Make sure it's in the same directory.")
        except ValueError as ve:
            self.show_error(f"❌ Input Error: {str(ve)}")
        except Exception as e:
            self.show_error(f"❌ Unexpected Error: {str(e)}")
            print(f"Full error: {e}")

    def show_success(self, message):
        if hasattr(self.ids, 'status'):
            self.ids.status.text = message
            self.ids.status.color = (0.2, 0.8, 0.2, 1)

    def show_error(self, message):
        if hasattr(self.ids, 'status'):
            self.ids.status.text = message
            self.ids.status.color = (0.9, 0.2, 0.2, 1)

    def clear_inputs_only(self):
        if not hasattr(self.ids, 'products_grid'):
            return
            
        for row in self.ids.products_grid.children:
            if hasattr(row, 'ids') and hasattr(row.ids, 'qty_input'):
                row.ids.qty_input.text = ""
        
        if hasattr(self.ids, 'expenditure'):
            self.ids.expenditure.text = ""
            
        self.calculate_preview()

    def clear_all(self):
        self.clear_inputs_only()
        
        if hasattr(self.ids, 'status'):
            self.ids.status.text = "Ready to generate report..."
            self.ids.status.color = (0.7, 0.7, 0.7, 1)

    def quick_fill_sample(self):
        """Fill with sample data for testing"""
        if not hasattr(self.ids, 'products_grid'):
            return
            
        # Sample quantities for first few products
        sample_data = [2, 1, 4, 1, 2, 1, 3, 0, 1, 2]
        rows = list(reversed(self.ids.products_grid.children))
        
        for i, row in enumerate(rows):
            if i < len(sample_data) and hasattr(row, 'ids') and hasattr(row.ids, 'qty_input'):
                if sample_data[i] <= row.stock and sample_data[i] > 0:
                    row.ids.qty_input.text = str(sample_data[i])
        
        if hasattr(self.ids, 'expenditure'):
            self.ids.expenditure.text = "2000"
            
        self.calculate_preview()

    def search_products(self, search_text):
        """Search products by name"""
        if not search_text:
            self.apply_filters()
            return
            
        if self.db:
            all_products = self.db.get_products()
        else:
            all_products = self.products_data
            
        self.products_data = [p for p in all_products if search_text.lower() in p["name"].lower()]
        self.populate_products()

class RubyApp(App):
    def build(self):
        self.title = "Bar Stock Management System"
        try:
            Builder.load_file('bar.kv')
        except Exception as e:
            print(f"KV load error: {e}")
        return SalesForm()
    
    def on_start(self):
        print("Bar Stock Management System started successfully!")
    
    def on_stop(self):
        # Close database connection when app stops
        root = self.root
        if hasattr(root, 'db') and root.db:
            root.db.close()

if __name__ == "__main__":
    try:
        RubyApp().run()
    except Exception as e:
        print(f"Error starting app: {e}")
        input("Press Enter to exit...")