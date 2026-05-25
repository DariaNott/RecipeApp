# Recipe Management System
A full-stack web application designed for organizing, searching, and managing culinary recipes. Built with Python (Flask) and SQLAlchemy, featuring a hybrid data persistence strategy and a custom search engine.

## Live Demo
[Demo website](https://myrecipes-y6km.onrender.com)

## Key Features
* __Advanced Search Engine:__ Implemented a custom Unicode-aware search logic to handle Cyrillic case-insensitivity in SQLite.
* __Hierarchical Categories:__ Nested category support with recursive data fetching (e.g., viewing "Main Dishes" also shows recipes from "Meat" and "Fish" subcategories).
* __Dynamic UI:__ Responsive interface with AJAX-powered sorting, filtering, and server-side pagination.
* __Admin Dashboard:__ Secure CRUD operations for recipes, ingredients, and categories using Flask-Login and Flask-WTF.
* __Rich Text Support:__ Integrated Flask-CKEditor for detailed, formatted cooking instructions.
* __"Cloud-Native" Architecture:__ Configured for seamless deployment on Render with automated database initialization from JSON sources.

## Tech Stack
* __Backend:__ Python 3.13, Flask, SQLAlchemy (ORM), SQLite.
* __Frontend:__ Jinja2, Bootstrap 5, JavaScript (ES6), AJAX.
* __Deployment:__ Gunicorn, Render, GitHub Actions.

## Technical Challenges & Solutions
### The SQLite Cyrillic Case-Sensitivity Problem
__Challenge:__ SQLite's default NOCASE collation only works for ASCII characters. It treats "Шарлотка" and "шарлотка" as different strings, which broke the search functionality for Ukrainian language.

__Solution:__ Registered a custom Python function `py_lower` within the SQLite connection context via SQLAlchemy events. This allowed the database to leverage Python’s robust Unicode support for string comparisons.

### Hybrid Data Persistence
__Challenge:__ Render's free tier uses an ephemeral file system, meaning SQLite files are wiped on every restart/deploy.

__Solution:__ Developed an automated synchronization pipeline. The app stores the "source of truth" in Git-persistent JSON files. Upon startup, a boot-script checks the database state and automatically restores/populates the SQL schema if it's empty.

## Project Structure
```
├── instance/               # SQLite database storage
├── resources/              # JSON files with seed data
├── static/                 # CSS, JS, and image assets
├── templates/              # Jinja2 HTML templates
├── app.py                  # Main application logic & configuration
├── models.py               # SQLAlchemy database models
├── forms.py                # Flask-WTF form definitions
├── importer.py             # Data migration & seeding script
```

## Installation & Setup
1. Clone the repository:
```
git clone https://github.com/yourusername/recipe-app.git
cd recipe-app
```
2. Create a virtual environment and install dependencies:

```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
3. Set Environment Variables:

Create a .env file or set them in your terminal:
``` 
export FLASK_KEY='your-secret-key'
export ADMIN_PASSWORD='your-admin-password'
```

4. Initialize the database with seed data:
```
python import_all.py
```

5. Run the application:
``` 
flask run
```
## License
Distributed under the MIT License. See LICENSE for more information.