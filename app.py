import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from werkzeug.utils import secure_filename
from twilio.rest import Client
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# --- DECOUPLED INITIALIZATION ---
# Create the extension objects globally, but without attaching them to an app.
# They will be connected to the app inside our "factory" function.
db = SQLAlchemy()
scheduler = BackgroundScheduler(daemon=True)

# --- CONFIGURATION (Global variables) ---
SENDER_EMAIL = os.environ.get('GMAIL_USER')
SENDER_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
OWNER_EMAIL = os.environ.get('GMAIL_USER')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- DATABASE MODELS ---
# These are defined here and will be linked to the database by the factory.
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    tools = db.relationship('Tool', backref='category', lazy=True)
    def __repr__(self): return f'<Category {self.name}>'

class Tool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    image_file = db.Column(db.String(100), nullable=True, default='default.jpg')
    status = db.Column(db.String(20), nullable=False, default='Available')
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    def __repr__(self): return f'<Tool {self.name}>'

class Borrower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    phone_number = db.Column(db.String(15), unique=True, nullable=True)
    contact_method = db.Column(db.String(10), default='None')
    def __repr__(self): return f'<Borrower {self.name}>'

class CheckoutLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=False)
    borrower_id = db.Column(db.Integer, db.ForeignKey('borrower.id'), nullable=False)
    checkout_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    tool = db.relationship('Tool', backref=db.backref('logs', lazy=True))
    borrower = db.relationship('Borrower', backref=db.backref('logs', lazy=True))
    def __repr__(self): return f'<Log: {self.tool.name} -> {self.borrower.name}>'

# --- HELPER & NOTIFICATION FUNCTIONS ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email(recipient_email, subject, body, image_path=None):
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        print("CRITICAL ERROR: Email credentials not set.")
        return
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as fp:
                img = MIMEImage(fp.read())
            msg.attach(img)
        except Exception as e:
            print(f"Could not attach image. Error: {e}")
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Reminder email successfully sent to {recipient_email}")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to send email to {recipient_email}. Error: {e}")

def send_sms(recipient_phone, body):
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        print("CRITICAL ERROR: Twilio credentials are not set.")
        return
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(body=body, from_=TWILIO_PHONE_NUMBER, to=recipient_phone)
        print(f"SMS successfully sent to {recipient_phone}. SID: {message.sid}")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to send SMS to {recipient_phone}. Error: {e}")

# MODIFIED: The reminder job now needs the 'app' object to create a context
def send_reminders(app):
    with app.app_context():
        print(f"Scheduler running daily reminder job at {datetime.now()}...")
        today = date.today()
        tomorrow = today + timedelta(days=1)
        due_logs = CheckoutLog.query.filter(
            CheckoutLog.due_date < tomorrow,
            CheckoutLog.return_date == None
        ).all()
        if not due_logs:
            print("No tools are due or overdue today. Job finished.")
            return
        overdue_items, due_today_items = [], []
        for log in due_logs:
            borrower, tool = log.borrower, log.tool
            if borrower.contact_method == 'Email' and borrower.email:
                subject = f"Reminder: Tool '{tool.name}' is Due"
                body = f"Hi {borrower.name},\n\nThis is a reminder that the tool '{tool.name}' is due for return. Thank you."
                image_path_to_send = None
                if tool.image_file:
                    image_path_to_send = os.path.join(app.config['UPLOAD_FOLDER'], tool.image_file)
                send_email(borrower.email, subject, body, image_path=image_path_to_send)
            elif borrower.contact_method == 'SMS' and borrower.phone_number:
                body = f"Tool Tracker Reminder: Hi {borrower.name}, the '{tool.name}' is due for return today. Thank you."
                formatted_phone = borrower.phone_number if borrower.phone_number.startswith('+') else f"+91{borrower.phone_number}"
                send_sms(formatted_phone, body)
            item_details = f"- {tool.name} (with {borrower.name})"
            if log.due_date.date() < today:
                overdue_items.append(item_details)
            else:
                due_today_items.append(item_details)
        if OWNER_EMAIL and (overdue_items or due_today_items):
            summary_subject = f"Daily Tool Tracker Summary - {today.strftime('%d %b %Y')}"
            summary_body = "Hello,\n\nHere is your daily summary:\n\n"
            if overdue_items:
                summary_body += "**OVERDUE ITEMS:**\n" + "\n".join(overdue_items) + "\n\n"
            if due_today_items:
                summary_body += "**DUE TODAY:**\n" + "\n".join(due_today_items) + "\n\n"
            send_email(OWNER_EMAIL, summary_subject, summary_body)
        print("Reminder job finished.")

# --- THE APPLICATION FACTORY ---
def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__)
    
    # --- CONFIGURATION ---
    app.config['SECRET_KEY'] = 'some-random-secret-string-to-keep-sessions-safe'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace("://", "ql://", 1)
    else:
        DB_USER = 'root'
        DB_PASSWORD = 'raj@mysql' # YOUR LOCAL PASSWORD
        DB_HOST = 'localhost'
        DB_NAME = 'tools_db' # YOUR LOCAL DB NAME
        app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql:/root:raj%40mysql@localhost/tools_db"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- INITIALIZE EXTENSIONS ---
    db.init_app(app)

    # --- REGISTER ROUTES ---
    @app.route('/')
    def dashboard():
        search_query = request.args.get('search', '')
        active_logs_query = CheckoutLog.query.filter_by(return_date=None)
        if search_query:
            active_logs_query = active_logs_query.join(Tool).join(Category).filter(
                or_(Tool.name.contains(search_query), Category.name.contains(search_query)))
        active_logs = active_logs_query.order_by(CheckoutLog.due_date).all()
        available_tools = Tool.query.filter_by(status='Available').order_by(Tool.name).all()
        all_borrowers = Borrower.query.order_by(Borrower.name).all()
        return render_template('index.html', active_logs=active_logs, available_tools=available_tools, all_borrowers=all_borrowers, today=date.today(), search_query=search_query)

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/trigger_reminders')
    def trigger_reminders():
        send_reminders(app)
        flash("Manual reminder check has been triggered.", "info")
        return redirect(url_for('dashboard'))
    
    @app.route('/checkout', methods=['POST'])
    def checkout():
        tool_id, borrower_id, due_date_str = request.form.get('tool_id'), request.form.get('borrower_id'), request.form.get('due_date')
        if not all([tool_id, borrower_id, due_date_str]):
            flash('All fields are required!', 'error'); return redirect(url_for('dashboard'))
        due_date_obj = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        due_date_end_of_day = datetime.combine(due_date_obj, datetime.max.time())
        tool = Tool.query.get(tool_id)
        if tool and tool.status == 'Available':
            tool.status = 'Checked Out'
            db.session.add(CheckoutLog(tool_id=tool_id, borrower_id=borrower_id, due_date=due_date_end_of_day))
            db.session.commit()
            flash(f'Success! "{tool.name}" checked out.', 'success')
        else: flash('Tool not available!', 'error')
        return redirect(url_for('dashboard'))

    @app.route('/check_in/<int:log_id>', methods=['POST'])
    def check_in(log_id):
        log = CheckoutLog.query.get(log_id)
        if log:
            log.return_date, log.tool.status = datetime.utcnow(), 'Available'
            db.session.commit()
            flash(f'"{log.tool.name}" checked in.', 'success')
        else: flash('Log entry not found!', 'error')
        return redirect(url_for('dashboard'))

    @app.route('/manage')
    def manage():
        return render_template('manage.html', all_tools=Tool.query.order_by(Tool.name).all(), all_borrowers=Borrower.query.order_by(Borrower.name).all(), all_categories=Category.query.order_by(Category.name).all())

    @app.route('/add_category', methods=['POST'])
    def add_category():
        name = request.form.get('category_name')
        if name and not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name)); db.session.commit()
            flash(f'Category "{name}" added.', 'success')
        else: flash('Category name is invalid or already exists.', 'error')
        return redirect(url_for('manage'))

    @app.route('/add_tool', methods=['POST'])
    def add_tool():
        name, cat_id = request.form.get('tool_name'), request.form.get('category_id')
        if 'tool_image' not in request.files:
            flash('No file part in the form!', 'error'); return redirect(url_for('manage'))
        file = request.files['tool_image']
        if not all([name, cat_id]):
            flash('Tool name and category are required.', 'error'); return redirect(url_for('manage'))
        if Tool.query.filter_by(name=name).first():
            flash('A tool with this name already exists.', 'error'); return redirect(url_for('manage'))
        filename = 'default.jpg'
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_tool = Tool(name=name, category_id=cat_id, image_file=filename)
        db.session.add(new_tool); db.session.commit()
        flash(f'Tool "{name}" added successfully.', 'success')
        return redirect(url_for('manage'))

    @app.route('/add_borrower', methods=['POST'])
    def add_borrower():
        name = request.form.get('borrower_name')
        if name:
            db.session.add(Borrower(name=name, email=request.form.get('email'), phone_number=request.form.get('phone'), contact_method=request.form.get('contact_method'))); db.session.commit()
            flash(f'Borrower "{name}" added.', 'success')
        else: flash('Borrower name is required.', 'error')
        return redirect(url_for('manage'))

    @app.route('/edit_borrower/<int:borrower_id>', methods=['GET', 'POST'])
    def edit_borrower(borrower_id):
        borrower_to_edit = Borrower.query.get_or_404(borrower_id)
        if request.method == 'POST':
            borrower_to_edit.name = request.form.get('borrower_name')
            borrower_to_edit.email = request.form.get('email')
            borrower_to_edit.phone_number = request.form.get('phone')
            borrower_to_edit.contact_method = request.form.get('contact_method')
            db.session.commit()
            flash(f'Borrower "{borrower_to_edit.name}" has been updated.', 'success')
            return redirect(url_for('manage'))
        return render_template('edit_borrower.html', borrower=borrower_to_edit)

    @app.route('/delete_tool/<int:tool_id>', methods=['POST'])
    def delete_tool(tool_id):
        tool_to_delete = Tool.query.get_or_404(tool_id)
        if tool_to_delete.status == 'Checked Out':
            flash(f'Error: Cannot delete "{tool_to_delete.name}" because it is currently checked out.', 'error')
            return redirect(url_for('manage'))
        if tool_to_delete.image_file and tool_to_delete.image_file != 'default.jpg':
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], tool_to_delete.image_file))
            except OSError as e:
                print(f"Error deleting image file {tool_to_delete.image_file}: {e}")
        db.session.delete(tool_to_delete)
        db.session.commit()
        flash(f'Tool "{tool_to_delete.name}" has been deleted.', 'success')
        return redirect(url_for('manage'))

    # --- START SCHEDULER ---
    if not scheduler.running:
        scheduler.add_job(
            id='daily_reminders_job',
            func=send_reminders,
            args=[app],
            trigger='cron',
            hour=8,
            minute=0
        )
        scheduler.start()
        print("Scheduler started successfully.")
        
    return app

# --- CREATE APP INSTANCE ---
app = create_app()

# --- RUN BLOCK FOR LOCAL TESTING ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, use_reloader=False, host='0.0.0.0')

