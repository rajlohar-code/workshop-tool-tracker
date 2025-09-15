Workshop Tool Tracker
A comprehensive web application designed to solve the real-world problem of tracking tools, equipment, and small parts in a busy workshop environment. This tool helps prevent loss of equipment, reduces downtime spent searching for items, and introduces accountability through a simple and efficient checkout system.

The project was born from a direct need observed in a fabrication and furniture workshop, making it a practical and user-focused solution. It is built to be mobile-friendly, allowing for easy use directly on the workshop floor.

Core Features
This application is packed with features designed to make workshop management seamless and efficient:

Tool & Borrower Management: Easily add, edit, or delete tools and authorized borrowers from the system.

Categorization & Search: Organize tools into custom categories (e.g., "Power Tools," "Hand Tools," "Drill Bits") and find items instantly with a powerful search that looks through both tool names and categories.

Visual Inventory: Upload photos for each tool, providing a quick visual reference that makes identification faster and reduces errors.

Simple Checkout/Check-In: A clean, intuitive interface for logging when a tool is borrowed and when it's returned, updating the tool's status in real-time.

Smart Dashboard: The main dashboard provides an at-a-glance view of all tools currently checked out, with color-coded due dates (Overdue, Due Today, Due Later) for immediate attention.

Automated Multi-Channel Reminders: The core intelligent feature of the application. The system automatically sends daily reminders to borrowers for tools that are due or overdue via:

Email Reminders: Sends a detailed email, including a photo of the tool.

SMS Reminders: Sends a direct text message for immediate notification, perfect for a workshop environment.

Daily Owner Summary: The workshop owner or manager receives a single, consolidated email every morning summarizing all due and overdue tools, eliminating the need to manually check the system.

Key Technologies Used
Backend: Python with the Flask web framework.

Database: MySQL (for local development) & PostgreSQL (for production deployment). SQLAlchemy is used as the ORM.

Frontend: HTML5, Tailwind CSS for responsive, mobile-first design.

Notifications:

Email: smtplib for sending emails via a Gmail SMTP server.

SMS: Twilio API for sending text message reminders.

Task Scheduling: APScheduler for running the daily reminder jobs automatically.

Deployment: The application is configured for deployment on a cloud platform like Render.

Future Improvements
The platform is designed to be extensible. Future planned features include:

Quantity Tracking for Consumables: The ability to track quantities of small, numerous items like drill bits, screws, or blades. This would allow the system to track not just who has a box of screws, but how many are left.

QR Code Integration: Generate a unique QR code for each tool. Users could simply scan a tool with their phone's camera to instantly bring up its status or check it in/out, dramatically speeding up the workflow.

Full Checkout History: A dedicated page to view the complete history of every transaction, allowing for analysis of tool usage, frequency, and borrower reliability over time.