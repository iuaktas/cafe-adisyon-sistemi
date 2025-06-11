import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import sqlite3
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
import shutil

DB_PATH = "adisyon.db"
CATEGORIES = ["Kahveler", "Soğuk İçecekler", "Tatlılar"]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " name TEXT, price REAL, category TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " table_no INTEGER, product_id INTEGER, quantity INTEGER, note TEXT)"
    )
    conn.commit()
    # Sample products
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        sample = [
            ("Espresso", 60, "Kahveler"),
            ("Latte", 70, "Kahveler"),
            ("Cappuccino", 75, "Kahveler"),
            ("Americano", 65, "Kahveler"),
            ("Mocha", 80, "Kahveler"),
            ("Türk Kahvesi", 55, "Kahveler")
        ]
        c.executemany(
            "INSERT INTO products (name, price, category) VALUES (?, ?, ?)", sample
        )
        conn.commit()
    conn.close()

class ProductManager(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Ürün Yönetimi")
        self.geometry("300x400")
        self.parent = parent
        self.selected_category = tk.StringVar(value=CATEGORIES[0])

        tk.Label(self, text="Kategori:").pack(pady=5)
        tk.OptionMenu(self, self.selected_category, *CATEGORIES).pack(fill="x", padx=10)

        tk.Label(self, text="Ürün Adı:").pack(pady=5)
        self.name_entry = tk.Entry(self)
        self.name_entry.pack(fill="x", padx=10)

        tk.Label(self, text="Fiyat (₺):").pack(pady=5)
        self.price_entry = tk.Entry(self)
        self.price_entry.pack(fill="x", padx=10)

        tk.Button(self, text="Ekle", command=self.add_product).pack(pady=10)

    def db(self):
        return sqlite3.connect(DB_PATH)

    def add_product(self):
        name = self.name_entry.get().strip()
        try:
            price = float(self.price_entry.get())
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz fiyat değeri.")
            return
        if not name:
            messagebox.showwarning("Uyarı", "Ürün adı giriniz.")
            return
        category = self.selected_category.get()

        conn = self.db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO products (name, price, category) VALUES (?, ?, ?)",
            (name, price, category)
        )
        conn.commit()
        conn.close()

        self.parent.load_products()
        self.destroy()

class CafeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kafe Adisyon Sistemi")
        self.geometry("1150x600")
        self.table_id = None
        init_db()
        self.create_widgets()

    def db(self):
        return sqlite3.connect(DB_PATH)

    def create_widgets(self):
        # Menu
        menu = tk.Menu(self)
        self.config(menu=menu)
        theme_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Tema", menu=theme_menu)
        theme_menu.add_command(label="Açık Mod", command=lambda: self.set_theme("light"))
        theme_menu.add_command(label="Koyu Mod", command=lambda: self.set_theme("dark"))
        menu.add_command(label="Veritabanı Yedekle", command=self.backup_db)
        menu.add_command(label="Veritabanı Geri Yükle", command=self.restore_db)

        # Sol panel: Masalar
        left = tk.Frame(self)
        left.pack(side="left", fill="y", padx=5, pady=5)
        tk.Label(left, text="Masalar").pack(pady=5)
        self.table_buttons = []
        for i in range(1, 16):
            btn = tk.Button(
                left, text=f"Masa {i}", width=10, height=2,
                command=lambda i=i: self.select_table(i)
            )
            btn.pack(pady=2)
            self.table_buttons.append(btn)

        # Orta panel: Ürün listesi
        mid = tk.Frame(self)
        mid.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        tk.Label(mid, text="Ürünler").pack(pady=5)
        self.category_var = tk.StringVar(value="Tümü")
        tk.OptionMenu(
            mid, self.category_var, "Tümü", *CATEGORIES,
            command=lambda _: self.load_products()
        ).pack(fill="x", padx=10)
        self.prod_list = tk.Listbox(mid)
        self.prod_list.pack(fill="both", expand=True, padx=10, pady=5)
        tk.Button(mid, text="Ekle", command=self.add_order).pack(pady=5)
        tk.Button(mid, text="Ürünleri Yönet", command=self.open_product_manager).pack(pady=5)
        tk.Button(mid, text="Siparişi Taşı", command=self.move_order).pack(pady=5)

        # Sağ panel: Siparişler
        right = tk.Frame(self)
        right.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        tk.Label(right, text="Siparişler").pack(pady=5)
        self.order_list = tk.Listbox(right)
        self.order_list.pack(fill="both", expand=True, padx=10)
        self.detail_label = tk.Label(right, text="Detay: -")
        self.detail_label.pack(pady=5)
        self.total_label = tk.Label(right, text="Toplam: 0₺")
        self.total_label.pack(pady=5)
        tk.Button(right, text="Adet +", command=self.increase_quantity).pack(pady=2)
        tk.Button(right, text="Adet -", command=self.decrease_quantity).pack(pady=2)
        tk.Button(right, text="Siparişi Sil", command=self.delete_order).pack(pady=2)
        tk.Button(right, text="Ürün Bazlı Kısmi Ödeme", command=self.partial_payment).pack(pady=2)
        tk.Button(right, text="Hesabı Kapat", command=self.close_account).pack(pady=2)
        tk.Button(right, text="Adisyon Yazdır", command=self.print_receipt).pack(pady=2)
        self.order_list.bind("<<ListboxSelect>>", self.update_detail_panel)

        # Load initial
        self.load_products()
        self.update_table_colors()

    def set_theme(self, mode):
        bg = "white" if mode == "light" else "#2e2e2e"
        fg = "black" if mode == "light" else "white"
        self.configure(bg=bg)
        for w in self.winfo_children():
            try:
                w.configure(bg=bg, fg=fg)
            except:
                pass

    def backup_db(self):
        target = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite DB", "*.db")]
        )
        if target:
            shutil.copyfile(DB_PATH, target)
            messagebox.showinfo("Yedekleme", "Veritabanı yedeklendi.")

    def restore_db(self):
        source = filedialog.askopenfilename(
            filetypes=[("SQLite DB", "*.db")]
        )
        if source:
            shutil.copyfile(source, DB_PATH)
            messagebox.showinfo("Geri Yükleme", "Veritabanı geri yüklendi.")
            self.load_products()
            if self.table_id:
                self.select_table(self.table_id)
            self.update_table_colors()

    def open_product_manager(self):
        ProductManager(self)

    def select_table(self, table_no):
        self.table_id = table_no
        self.load_orders()

    def load_products(self):
        self.prod_list.delete(0, tk.END)
        conn = self.db()
        c = conn.cursor()
        sel = self.category_var.get()
        if sel == "Tümü":
            c.execute("SELECT id, name, price FROM products")
        else:
            c.execute(
                "SELECT id, name, price FROM products WHERE category=?", (sel,)
            )
        self.products = c.fetchall()
        conn.close()
        for pid, name, price in self.products:
            self.prod_list.insert(tk.END, f"{name} - {price}₺")

    def add_order(self):
        if self.table_id is None:
            messagebox.showwarning("Uyarı", "Önce masa seçin.")
            return
        sel = self.prod_list.curselection()
        if not sel:
            messagebox.showwarning("Uyarı", "Lütfen ürün seçin.")
            return
        pid = self.products[sel[0]][0]
        note = simpledialog.askstring("Not", "Opsiyonel not:") or ""
        conn = self.db()
        c = conn.cursor()
        c.execute(
            "SELECT id, quantity FROM orders WHERE table_no=? AND product_id=?", 
            (self.table_id, pid)
        )
        row = c.fetchone()
        if row:
            c.execute(
                "UPDATE orders SET quantity=quantity+1 WHERE id=?", (row[0],)
            )
        else:
            c.execute(
                "INSERT INTO orders (table_no, product_id, quantity, note) VALUES (?, ?, ?, ?)",
                (self.table_id, pid, 1, note)
            )
        conn.commit()
        conn.close()
        self.load_orders()
        self.update_table_colors()

    def load_orders(self):
        if self.table_id is None:
            return
        self.order_list.delete(0, tk.END)
        conn = self.db()
        c = conn.cursor()
        c.execute(
            "SELECT orders.id, products.name, products.price, orders.quantity, orders.note "
            "FROM orders JOIN products ON orders.product_id=products.id "
            "WHERE orders.table_no=?",
            (self.table_id,)
        )
        self.current_orders = c.fetchall()
        conn.close()
        total = 0
        for oid, name, price, qty, note in self.current_orders:
            self.order_list.insert(tk.END, f"{name} x{qty} - {price*qty}₺")
            total += price * qty
        self.total_label.config(text=f"Toplam: {total}₺")

    def increase_quantity(self):
        sel = self.order_list.curselection()
        if not sel:
            return
        oid = self.current_orders[sel[0]][0]
        conn = self.db()
        c = conn.cursor()
        c.execute("UPDATE orders SET quantity=quantity+1 WHERE id=?", (oid,))
        conn.commit()
        conn.close()
        self.load_orders()

    def decrease_quantity(self):
        sel = self.order_list.curselection()
        if not sel:
            return
        oid, qty = self.current_orders[sel[0]][0], self.current_orders[sel[0]][3]
        conn = self.db()
        c = conn.cursor()
        if qty <= 1:
            c.execute("DELETE FROM orders WHERE id=?", (oid,))
        else:
            c.execute("UPDATE orders SET quantity=quantity-1 WHERE id=?", (oid,))
        conn.commit()
        conn.close()
        self.load_orders()

    def delete_order(self):
        sel = self.order_list.curselection()
        if not sel:
            return
        oid = self.current_orders[sel[0]][0]
        conn = self.db()
        c = conn.cursor()
        c.execute("DELETE FROM orders WHERE id=?", (oid,))
        conn.commit()
        conn.close()
        self.load_orders()

    def partial_payment(self):
        sel = self.order_list.curselection()
        if not sel:
            messagebox.showwarning("Uyarı", "Önce bir sipariş seçin.")
            return
        oid, name, price, qty, note = self.current_orders[sel[0]]
        item_total = price * qty
        amt = simpledialog.askfloat(
            "Kısmi Ödeme",
            f"{name} için ödenecek tutarı girin:",
            minvalue=0,
            maxvalue=item_total
        )
        if amt is None:
            return
        remaining = item_total - amt
        conn = self.db()
        c = conn.cursor()
        if remaining <= 0:
            c.execute("DELETE FROM orders WHERE id=?", (oid,))
        else:
            # Kalan miktarı adete çevir
            new_qty = int(remaining // price)
            c.execute(
                "UPDATE orders SET quantity=?, note=? WHERE id=?",
                (new_qty, note, oid)
            )
        conn.commit()
        conn.close()
        self.load_orders()
        self.update_table_colors()

    def close_account(self):
        if self.table_id is None:
            return
        conn = self.db()
        c = conn.cursor()
        c.execute("DELETE FROM orders WHERE table_no=?", (self.table_id,))
        conn.commit()
        conn.close()
        self.load_orders()
        self.update_table_colors()

    def print_receipt(self):
        if not getattr(self, "current_orders", None):
            messagebox.showwarning("Uyarı", "Yazdırılacak sipariş yok.")
            return
        fn = f"adisyon_{self.table_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        pdf = canvas.Canvas(fn, pagesize=A4)
        y = 800
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, f"Masa {self.table_id} Adisyon")
        y -= 30
        pdf.setFont("Helvetica", 12)
        total = 0
        for _, name, price, qty, note in self.current_orders:
            pdf.drawString(50, y, f"{name} x{qty} = {price*qty}₺")
            y -= 20
            if note:
                pdf.drawString(60, y, f"Not: {note}")
                y -= 20
            total += price * qty
        pdf.drawString(50, y - 10, f"Toplam: {total}₺")
        pdf.save()
        messagebox.showinfo("PDF", f"Oluşturuldu: {fn}")

    def update_detail_panel(self, event):
        sel = self.order_list.curselection()
        if not sel:
            self.detail_label.config(text="Detay: -")
        else:
            _, name, price, qty, note = self.current_orders[sel[0]]
            self.detail_label.config(
                text=f"Detay: {name} | Adet: {qty} | Not: {note if note else '-'}"
            )

    def update_table_colors(self):
        conn = self.db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT table_no FROM orders")
        active = {row[0] for row in c.fetchall()}
        conn.close()
        for i, btn in enumerate(self.table_buttons, start=1):
            btn.config(bg="lightgreen" if i in active else "lightgray")

    def move_order(self):
        if self.table_id is None:
            messagebox.showwarning("Uyarı", "Taşımak için önce bir masa seçmelisiniz.")
            return
        new_table = simpledialog.askinteger(
            "Masa Taşı",
            "Hangi masaya taşımak istiyorsunuz?",
            minvalue=1,
            maxvalue=15
        )
        if new_table and new_table != self.table_id:
            conn = self.db()
            c = conn.cursor()
            c.execute(
                "UPDATE orders SET table_no=? WHERE table_no=?",
                (new_table, self.table_id)
            )
            conn.commit()
            conn.close()
            self.select_table(new_table)
            self.update_table_colors()
            messagebox.showinfo(
                "Bilgi",
                f"Siparişler Masa {new_table}'ye taşındı."
            )

if __name__ == "__main__":
    app = CafeApp()
    app.mainloop()
