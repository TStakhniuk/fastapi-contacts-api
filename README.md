# ContactHub API 🚀

A powerful and secure REST API for contact management, built with the modern FastAPI framework. This application provides a full suite of features for managing contacts, complete with user authentication, email verification, rate limiting, and much more.

## ✨ Key Features

- **Full CRUD Functionality:** Complete Create, Read, Update, and Delete operations for contacts.
- **Advanced Search:** Easily find contacts by name, surname, or email.
- **Upcoming Birthdays:** Get an automatic list of contacts with birthdays in the next 7 days.
- **Secure Authentication:** Robust user authentication system with email verification and password reset functionality.
- **JWT Authorization:** Protected endpoints using JWT access and refresh tokens, ensuring users can only access their own data.
- **User Profiles & Avatars:** Users can view their profiles and upload custom avatars to [Cloudinary](https://cloudinary.com/).
- **High Performance:** [Redis](https://redis.io/) caching for frequently accessed data and optimized database queries with SQLAlchemy.
- **Enhanced Security:** Password hashing with `bcrypt`, rate limiting on sensitive endpoints to prevent abuse, and CORS support.
- **Automatic & Manual Documentation:**
  - Auto-generated interactive API documentation via Swagger UI and ReDoc.
  - Comprehensive project documentation generated with [Sphinx](https://www.sphinx-doc.org/).

## 🚀 Getting Started

Follow these steps to set up and run the project locally.

### 1. Clone the Repository

```bash
git clone https://github.com/TStakhniuk/fastapi-contacts-api.git
cd fastapi-contacts-api
```

### 2. Install Dependencies

This single command will create a virtual environment and install all required packages from the `pyproject.toml` file.

```bash
poetry install
```

### 3. Set Up Environment Variables

Copy the `.env.example` file to `.env` and fill in your configuration details.

```bash
cp .env.example .env
```

You need to configure these essential variables in your `.env` file:

```env
# Database PostgreSQL
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=your_db_name
POSTGRES_TEST_DB=your_test_db_name
POSTGRES_HOST=your_db_host
POSTGRES_PORT=your_db_port
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
DATABASE_TEST_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_TEST_DB}

# JWT authentication
SECRET_KEY=your_secret_key
ALGORITHM=your_algorithm

# Email service
MAIL_USERNAME=your_email@example.com
MAIL_PASSWORD=your_password
MAIL_FROM=your_email@example.com
MAIL_PORT=your_port
MAIL_SERVER=your_server

# Redis
REDIS_HOST=your_redis_host
REDIS_PORT=your_redis_host
REDIS_PASSWORD=your_redis_password

# Cloud storage
CLOUDINARY_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### 4. Start the Application with Docker Compose

This single command will build and start the API, the PostgreSQL database, and the Redis cache.

```bash
docker-compose up -d --build
```

The API will be available at `http://localhost:8000`.

### 5. Run Database Migrations

Apply the database migrations using Alembic to set up your database schema:

```bash
docker-compose exec web alembic upgrade head
```

If you're running locally without Docker:

```bash
alembic upgrade head
```

### 6. Access the Documentation

Once the application is running, you can access the interactive API documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`


## 📖 API Endpoints

A brief overview of the available endpoints. For full details and to try them out live, please visit the interactive Swagger UI documentation.

All endpoints under `/contacts` and `/users` require authentication.

### Authentication (`/auth`)

Handles user registration, login, and account verification processes.

- `POST /signup`: Register a new user.
- `GET /verify-email`: Verify email with a token sent to the user.
- `POST /resend-verification`: Resend the verification email if the previous one expired.
- `POST /login`: Authenticate a user and receive a pair of JWT tokens (access and refresh).
- `POST /refresh`: Obtain a new access token using a valid refresh token.
- `POST /reset-password`: Request a password reset link to be sent via email.
- `POST /reset-password/confirm`: Confirm and set a new password using a token.

### Contacts (`/contacts`)

Provides full CRUD functionality for managing a user's contacts.

- `GET /`: Get a paginated list of the current user's contacts.
- `POST /`: Create a new contact.
- `GET /{contact_id}`: Retrieve a single contact by its ID.
- `PUT /{contact_id}`: Update an existing contact by its ID.
- `DELETE /{contact_id}`: Delete a contact by its ID.
- `GET /search/`: Search for contacts by name, surname, or email.
- `GET /birthdays/`: Get a list of contacts with birthdays in the next 7 days.

### Users (`/users`)

Endpoints for managing user-specific data.

- `GET /me`: Get the profile information of the currently authenticated user.
- `PATCH /avatar`: Update the avatar for the current user. Requires a file upload.

## ⚡ Rate Limiting

The API implements rate limiting on sensitive endpoints to ensure stability and security:

-   **Create Contact** (`POST /contacts/`): 5 requests per minute.
-   **Update Contact** (`PUT /contacts/{contact_id}`): 10 requests per minute.
-   **Delete Contact** (`DELETE /contacts/{contact_id}`): 10 requests per minute.
-   **Upcoming Birthdays** (`GET /contacts/birthdays/`): 10 requests per minute.
-   **Search Contacts** (`GET /contacts/search/`): 15 requests per minute.
-   **Get All Contacts** (`GET /contacts/`): 20 requests per minute.
-   **Get Single Contact** (`GET /contacts/{contact_id}`): 20 requests per minute.

## 📚 Sphinx Documentation

This project includes comprehensive, pre-generated documentation created with Sphinx. The HTML files are already included in the repository.

To view the documentation, simply open the file **`docs/_build/html/index.html`** in your web browser.