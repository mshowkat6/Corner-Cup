from flask import Flask, render_template, request, redirect
import mysql.connector
from datetime import datetime
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Database connection configuration
db_config = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME')
}

def fetch_all_tables():
    tables = [
        'GeneralSupplies', 'DogTreats', 'SpreadsAndCondiments', 'Teas',
        'CoolerDrinks', 'SyrupsAndSauces', 'Oatmeals', 'Cereals',
        'FrappePowders', 'SmoothiePurees', 'CleaningAndSanitarySupplies',
        'Lids', 'Cups', 'TableWare', 'SugarStationSupplies',
        'TogoSupplies', 'SnackSupplies', 'GeneralDrinkIngredients'
    ]
    data = {}
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    for table in tables:
        query = f"SELECT * FROM {table}"
        cursor.execute(query)
        data[table] = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

def update_table(table_name, product_ids, quantities, notes_list):
    entry_date = datetime.now().date()
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    for product_id, quantity, notes in zip(product_ids, quantities, notes_list):
        if quantity == '':
            quantity = 0
        query = f"""
            UPDATE {table_name}
            SET Quantity = %s, NotesToMichael = %s, EntryDate = %s
            WHERE ProductID = %s
        """
        cursor.execute(query, (int(quantity), notes, entry_date, product_id))
    conn.commit()
    cursor.close()
    conn.close()

def fetch_combined_bring_to_main():
    tables = [
        'GeneralSupplies', 'DogTreats', 'SpreadsAndCondiments', 'Teas',
        'CoolerDrinks', 'SyrupsAndSauces', 'Oatmeals', 'Cereals',
        'FrappePowders', 'SmoothiePurees', 'CleaningAndSanitarySupplies',
        'Lids', 'Cups', 'TableWare', 'SugarStationSupplies',
        'TogoSupplies', 'SnackSupplies', 'GeneralDrinkIngredients'
    ]
    combined_data = []
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    for table in tables:
        query = f"SELECT ProductName, Quantity, ItemType, MainPar, (MainPar - Quantity) AS BringToMain, NotesToMichael, EntryDate FROM {table} WHERE (MainPar - Quantity) > 0"
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            row['TableName'] = table
            combined_data.append(row)
    cursor.close()
    conn.close()
    return combined_data

@app.route('/')
def index():
    data = fetch_all_tables()
    return render_template('index.html', data=data)

@app.route('/update', methods=['POST'])
def update():
    try:
        for table_name in request.form.getlist('table_name[]'):
            product_ids = request.form.getlist(f'product_id_{table_name}[]')
            quantities = request.form.getlist(f'quantity_{table_name}[]')
            notes_list = request.form.getlist(f'notes_{table_name}[]')
            update_table(table_name, product_ids, quantities, notes_list)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return str(e), 500
    return redirect('/bring_to_main')

@app.route('/bring_to_main')
def bring_to_main():
    combined_data = fetch_combined_bring_to_main()
    return render_template('bring_to_main.html', combined_data=combined_data)

@app.route('/send_email', methods=['POST'])
def send_email():
    # Michael's email address
    michael_email = 'maymunah.showkat@gmail.com'
    
    combined_data = fetch_combined_bring_to_main()
    
    # Create email content
    html_content = render_template('email_template.html', combined_data=combined_data)

    # Email setup
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Bring to Main Inventory"
    msg['From'] = os.getenv('EMAIL_USER')
    msg['To'] = michael_email
    msg.attach(MIMEText(html_content, 'html'))

    # Send email
    try:
        smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
        smtp_server.starttls()
        smtp_server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASSWORD'))
        smtp_server.sendmail(msg['From'], [msg['To']], msg.as_string())
        smtp_server.quit()
        return redirect('/bring_to_main')
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)
