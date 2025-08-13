from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.clock import Clock
from report_generator import generate_report
import os
from datetime import datetime
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner

# Enhanced product data with categories and subcategories
PRODUCTS = [
    # Beers - Bottles
    {"name": "Tusker Lager", "stock": 40, "price": 250, "category": "Beer", "subcategory": "Bottle", "icon": "🍺"},
    {"name": "WhiteCap", "stock": 30, "price": 250, "category": "Beer", "subcategory": "Bottle", "icon": "🍺"},
    {"name": "Guinness", "stock": 25, "price": 250, "category": "Beer", "subcategory": "Bottle", "icon": "🍺"},
    {"name": "Heineken Bottle", "stock": 20, "price": 300, "category": "Beer", "subcategory": "Bottle", "icon": "🍺"},
    
    # Beers - Cans
    {"name": "Tusker Cans", "stock": 35, "price": 270, "category": "Beer", "subcategory": "Can", "icon": "🍺"},
    {"name": "Guinness Cans", "stock": 25, "price": 270, "category": "Beer", "subcategory": "Can", "icon": "🍺"},
    
    # Wines - Red
    {"name": "4TH STREET RED", "stock": 15, "price": 800, "category": "Wine", "subcategory": "Red", "icon": "🍷"},
    {"name": "FOUR COUSINS RED", "stock": 12, "price": 850, "category": "Wine", "subcategory": "Red", "icon": "🍷"},
    
    # Wines - White
    {"name": "4TH STREET WHITE", "stock": 10, "price": 800, "category": "Wine", "subcategory": "White", "icon": "🍷"},
    
    # Whiskeys
    {"name": "J/W BlackLabel", "stock": 8, "price": 1200, "category": "Whiskey", "subcategory": "Premium", "icon": "🥃"},
    {"name": "J/W Red Label", "stock": 12, "price": 900, "category": "Whiskey", "subcategory": "Standard", "icon": "🥃"},
    
    # Spirits
    {"name": "KONYANGI", "stock": 20, "price": 400, "category": "Spirit", "subcategory": "Local", "icon": "🍸"},
    
    # Soft Drinks
    {"name": "Soda 500ml", "stock": 50, "price": 100, "category": "Soft Drink", "subcategory": "Soda", "icon": "🥤"},
    
    # Snacks
    {"name": "Samosa", "stock": 30, "price": 50, "category": "Snack", "subcategory": "Food", "icon": "🥟"},
]

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

class SalesForm(BoxLayout):
    total_revenue = NumericProperty(0)
    total_items_sold = NumericProperty(0)
    current_category = StringProperty("All")
    current_subcategory = StringProperty("All")
    categories = ListProperty(["All"])
    subcategories = ListProperty(["All"])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.products_data = PRODUCTS.copy()
        self.categories = ["All"] + sorted(list(set(p["category"] for p in PRODUCTS)))
        self.subcategories = ["All"]
        self.initialized = False
        Clock.schedule_once(self._delayed_init, 0.3)
    
    def _delayed_init(self, dt):
        if not self.initialized:
            self.populate_products()
            self.initialized = True
    
    def update_subcategories(self, category):
        if category == "All":
            self.subcategories = ["All"]
        else:
            subs = set(p["subcategory"] for p in PRODUCTS if p["category"] == category)
            self.subcategories = ["All"] + sorted(list(subs))
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
        if self.current_category == "All":
            self.products_data = PRODUCTS.copy()
        else:
            self.products_data = [p for p in PRODUCTS if p["category"] == self.current_category]
            if self.current_subcategory != "All":
                self.products_data = [p for p in self.products_data if p["subcategory"] == self.current_subcategory]
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
                subcategory=item["subcategory"],
                icon=item["icon"]
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
                    "Stock Before": row.stock,
                    "Quantity Sold": qty_sold,
                    "Price Per Unit": row.price,
                    "Total Sale": sale_amount,
                    "Stock After": row.stock - qty_sold
                })
            
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

            for row in self.ids.products_grid.children:
                qty_sold = 0
                if hasattr(row, 'ids') and hasattr(row.ids, 'qty_input'):
                    qty_text = row.ids.qty_input.text
                    if qty_text and qty_text.isdigit():
                        qty_sold = int(qty_text)
                
                for product in self.products_data:
                    if product["name"] == row.product_name:
                        product["stock"] -= qty_sold
                        break
            
            net_profit = total_sales - expenditure
            profit_status = "Profit" if net_profit >= 0 else "Loss"
            
            self.show_success(
                f"✅ Report generated successfully!\n"
                f"📁 File: {os.path.basename(report_path)}\n"
                f"💰 Total Sales: Ksh {total_sales:,}\n"
                f"💳 Expenditure: Ksh {expenditure:,}\n"
                f"📊 Net {profit_status}: Ksh {abs(net_profit):,}"
            )
            
            self.clear_inputs_only()
            self.populate_products()

        except FileNotFoundError:
            self.show_error("❌ Error: report_generator.py not found")
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
        if not hasattr(self.ids, 'products_grid'):
            return
            
        sample_data = [3, 2, 4, 1, 2]
        rows = list(reversed(self.ids.products_grid.children))
        
        for i, row in enumerate(rows):
            if i < len(sample_data) and hasattr(row, 'ids') and hasattr(row.ids, 'qty_input'):
                if sample_data[i] <= row.stock:
                    row.ids.qty_input.text = str(sample_data[i])
        
        if hasattr(self.ids, 'expenditure'):
            self.ids.expenditure.text = "1500"
            
        self.calculate_preview()

class BarApp(App):
    def build(self):
        self.title = "Bar Sales Manager Pro"
        return SalesForm()
    
    def on_start(self):
        print("Bar Sales Manager Pro started successfully!")

if __name__ == "__main__":
    try:
        BarApp().run()
    except Exception as e:
        print(f"Error starting app: {e}")
        input("Press Enter to exit...")