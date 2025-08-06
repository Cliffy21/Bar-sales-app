from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from report_generator import generate_report
from kivy.metrics import dp

class SalesForm(BoxLayout):
    def submit(self):
        try:
            data = [
                {
                    'Item Name': self.ids.item_name.text,
                    'Stock Before': int(self.ids.stock_before.text),
                    'Quantity Sold': int(self.ids.quantity_sold.text),
                    'Price Per Unit': float(self.ids.price.text)
                }
            ]
            expenditure = float(self.ids.expenditure.text)

            report_path = generate_report(data, expenditure)
            self.ids.status.text = f"✅ Report saved at:\n{report_path}"

        except Exception as e:
            self.ids.status.text = f"❌ Error: {str(e)}"

class BarApp(App):
    def build(self):
        return SalesForm()

if __name__ == "__main__":
    BarApp().run()
