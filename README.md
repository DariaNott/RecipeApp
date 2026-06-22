# Recipe Management System
A full-stack web application designed for organizing, searching, and managing culinary recipes. Built with Python (Flask) and SQLAlchemy, featuring a hybrid data persistence strategy and a custom search engine.

## Key Features
* __Advanced Search Engine:__ Implemented a custom Unicode-aware search logic to handle Cyrillic case-insensitivity in SQLite.
* __Hierarchical Categories:__ Nested category support with recursive data fetching (e.g., viewing "Main Dishes" also shows recipes from "Meat" and "Fish" subcategories).
* __Smart Category Mapping:__ Simplifies recipe creation by resolving plain text strings (`category_names`) to database records automatically on the backend.
* __Dynamic UI:__ Responsive interface with AJAX-powered sorting, filtering, and server-side pagination.
* __Asynchronous Architecture:__ Built completely on an async/await pipeline using `AsyncSession` to maximize concurrent request throughput.
* __Secured Admin API:__ Full CRUD operations protected by a custom `X-API-KEY` dependency injection barrier for secure backend management.
* __MissingGreenlet Prevention:__ Implements explicit eager loading strategies via `selectinload` to reliably handle complex Many-to-Many and One-to-Many relational fetches under async constraints.
* __Strict Schema Validation:__ Streamlined JSON payloads compiled with **Pydantic v2**, ensuring type-safety while isolating the database from clients.

## Tech Stack
* __Backend:__ Python 3.13, FastAPI (ASGI)
* __ORM:__ SQLAlchemy 2.0 (Async Mode)
* __Data Validation:__ Pydantic v2
* __Database Drivers:__ `asyncpg` (for PostgreSQL)
* __Frontend:__ Jinja2, Bootstrap 5, JavaScript (ES6), AJAX.
* __Deployment:__ Uvicorn

## Technical Challenges & Solutions
### Asynchronous ORM Eager Loading (The Greenlet Dilemma)
__Challenge:__ Lazy loading of relational tables (like fetching a recipe's instructions or ingredients) is natively synchronous. In an asynchronous FastAPI environment, accessing lazy-loaded attributes outside the initial session context throws a critical `MissingGreenlet` exception.

__Solution:__ Designed the database fetching strategy to utilize explicit eager loading with `selectinload`. Every `GET`, `POST`, and `PUT` route explicitly pre-loads the relational graphs (`categories`, `ingredients`, `instructions`, `tips`) within a unified query scope before passing data to Pydantic serializers.

### Streamlined Payload Conversion & Data Cleansing
__Challenge:__ Frontend clients and API consumers shouldn't have to keep track of nested database primary keys (`id`) when assigning categories or attaching new recipe parameters, nor should they handle deprecated fields.

__Solution:__ Designed input Pydantic contracts (`RecipeCreate`) to expect a natural array of strings (`category_names`). The backend seamlessly queries, validates, and links existing Category instances, and cleanly generates isolated rows for sub-tables on every submission.

## Project Structure
```
├── routers/
│   └── admin.py            # Protected administrative CRUD endpoints
│   └── web.py              # Public web endpoints
├── database.py             # Async engine setup & SessionLocal generator
├── dependencies.py         # Shared injection layers (get_db, verify_api_key)
├── main.py                 # Core application bootstrapper & OpenAPI metadata
├── models.py               # Async-mapped SQLAlchemy 2.0 database models
├── schemas.py              # Pydantic v2 data models & response serializers
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
export X_API_KEY='my_super_secret_recipe_app_key_123'
```

4. Run the application:
``` 
uvicorn main:app --reload
```
Once initialized, interact with the backend directly through:
* Interactive Swagger UI: http://127.0.0.1:8000/docs
* Alternative ReDoc UI: http://127.0.0.1:8000/redoc
## License
Distributed under the MIT License. See LICENSE for more information.