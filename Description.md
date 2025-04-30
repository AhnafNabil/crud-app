# Full-Stack CRUD Application with React, FastAPI, PostgreSQL, and Redis

This CRUD (Create, Read, Update, Delete) application follows a modern microservices-based architecture using Docker containers for isolation and easy deployment. The system is designed with a clear separation of concerns, where each component has well-defined responsibilities and communicates with others through standardized interfaces.

## System Architecture

![alt text](./images/System-Architecture.svg)

## Key Components

### 1. Frontend (React)
The frontend is a single-page application built with React that provides an intuitive user interface for managing items. It's served by Nginx, which also handles routing and proxying API requests to the backend.

![alt text](./images/image.png)

**Container Structure:**
- **Nginx**: Serves static files and proxies API requests
- **React Application**: Provides the user interface with components for listing, creating, editing, and deleting items
- **API Service**: Handles communication with the backend API

**Port Mapping:**
- External port 3000 → Container port 80

#### Nginx Configuration

Let's examine the key sections of our `nginx.conf` file:

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private auth;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/x-javascript application/xml application/json;
    gzip_disable "MSIE [1-6]\.";

    # Cache static assets
    location ~* \.(?:jpg|jpeg|gif|png|ico|svg|woff|woff2|ttf|css|js)$ {
        expires 7d;
        add_header Cache-Control "public";
    }

    # Handle React Router
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Error pages
    error_page 404 /index.html;
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}
```

#### Key Configuration Components:

1. **Basic Server Setup**:
   - `listen 80`: Nginx listens on port 80
   - `root /usr/share/nginx/html`: Serves files from this directory (React build output)
   - `index index.html`: Default file to serve

2. **Compression (gzip)**:
   - Reduces file sizes for faster loading
   - Configured for common web file types
   - Excludes old IE browsers that have issues with compression

3. **Static Asset Caching**:
   - `expires 7d`: Browser should cache static files for 7 days
   - Improves performance for returning visitors
   - Reduces server load and bandwidth usage

4. **React Router Support**:
   - `try_files $uri $uri/ /index.html`: First tries to find the exact file, then falls back to index.html
   - Essential for client-side routing in single-page applications
   - Allows users to bookmark or directly access any route

5. **API Proxying**:
   - `location /api/`: Matches requests starting with /api/
   - `proxy_pass http://backend:8000/`: Forwards requests to the backend container
   - Strips the /api prefix when forwarding
   - Various headers are set to properly handle proxying

6. **Error Handling**:
   - 404 errors return index.html (for React Router)
   - Server errors (500, 502, 503, 504) show a dedicated error page

#### Frontend Dockerfile

The frontend Dockerfile is a multi-stage build configuration that creates an optimized container for serving our React application. Let's break down each section to understand what it does:

```dockerfile
# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy app source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy the build output from the build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx server
CMD ["nginx", "-g", "daemon off;"]
```

#### Multi-Stage Build Explained

This Dockerfile uses a multi-stage build approach, which creates a smaller, more secure production image by separating the build environment from the runtime environment.

#### Stage 1: Build Stage

```dockerfile
# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy app source code
COPY . .

# Build the application
RUN npm run build
```

This stage does the following:

1. **Base Image**: Uses `node:18-alpine` - a lightweight Node.js 18 image based on Alpine Linux
2. **Working Directory**: Sets `/app` as the working directory
3. **Dependency Files**: Copies `package.json` and `package-lock.json` first (before the rest of the code) to leverage Docker's layer caching - if dependencies haven't changed, this layer can be reused
4. **Install Dependencies**: Uses `npm ci` (Clean Install) instead of `npm install` for more reliable and faster builds in CI/CD environments
5. **Source Code**: Copies the entire application source code into the container
6. **Build Process**: Runs `npm run build` to create a production-optimized build of the React application (creates the `build` directory with static files)

#### Stage 2: Production Stage

```dockerfile
# Production stage
FROM nginx:alpine

# Copy the build output from the build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx server
CMD ["nginx", "-g", "daemon off;"]
```

This stage does the following:

1. **Base Image**: Uses `nginx:alpine` - a lightweight Nginx image based on Alpine Linux
2. **Copy Build Output**: Copies only the build artifacts from the previous stage (`/app/build`) to Nginx's default HTML serving directory (`/usr/share/nginx/html`)
3. **Custom Nginx Config**: Copies our custom Nginx configuration file to the appropriate location in the Nginx container
4. **Port**: Explicitly documents that the container exposes port 80 (Nginx's default HTTP port)
5. **Command**: Starts Nginx in the foreground with `daemon off` to ensure proper signal handling and container lifecycle management

#### How This Works with Docker Compose

In our Docker Compose setup, the frontend service is configured to:

1. Build the image using this Dockerfile
2. Map external port 3000 to container port 80
3. Set environment variables needed for the application

### 2. Backend (FastAPI)
The backend is a Python-based REST API built with FastAPI that handles business logic, data validation, and interactions with the database and cache.

**Container Structure:**
- **FastAPI Application**: Provides RESTful API endpoints
- **SQLAlchemy ORM**: Manages database interactions
- **Pydantic Models**: Handles data validation
- **Cache Module**: Manages Redis caching operations

**Port Mapping:**
- External port 8000 → Container port 8000

#### Backend Dockerfile

The backend Dockerfile creates a container for running our FastAPI application with all its dependencies. Let's break down each section to understand what it does:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

The backend Dockerfile creates a container for our FastAPI application by:

1. **Base Image**: Uses `python:3.9-slim` - a lightweight Python image
2. **Working Directory**: Sets `/app` as the working location
3. **Dependencies**: 
   - Copies `requirements.txt` first (for better caching)
   - Installs Python packages with `pip install`
4. **Application Code**: Copies all backend code into the container
5. **Environment Setup**:
   - `PYTHONDONTWRITEBYTECODE=1`: Prevents `.pyc` files
   - `PYTHONUNBUFFERED=1`: Ensures logs appear in real-time
6. **Port Configuration**: Exposes port 8000 for API access
7. **Startup Command**: Runs the application with `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### 3. Database (PostgreSQL)
PostgreSQL provides persistent storage for the application data in a relational database structure.

**Container Structure:**
- **PostgreSQL Server**: Runs the database engine
- **Items Table**: Stores item data (id, title, description, is_active, created_at, updated_at)

**Port Mapping:**
- External port 5432 → Container port 5432

### 4. Cache (Redis)
Redis provides high-performance in-memory caching to reduce database load and improve response times.

**Container Structure:**
- **Redis Server**: In-memory data store
- **Cache Keys**: Organized by operation type (list, detail) with TTL

**Port Mapping:**
- External port 6379 → Container port 6379

## Docker Compose File Configuration

The Docker Compose file orchestrates our entire application, defining how all services work together. Here's a clear explanation:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:15
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=crudapp
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Backend API Service
  backend:
    build: ./backend
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_SERVER=db
      - POSTGRES_PORT=5432
      - POSTGRES_DB=crudapp
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # Frontend Service
  frontend:
    build: ./frontend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:80"
    depends_on:
      - backend
    environment:
      - REACT_APP_API_URL=/api

volumes:
  postgres_data:
  redis_data:
```

### Service Breakdown

#### 1. Database (PostgreSQL)
```yaml
db:
  image: postgres:15
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
  environment:
    - POSTGRES_USER=postgres
    - POSTGRES_PASSWORD=postgres
    - POSTGRES_DB=crudapp
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 5s
    retries: 5
```

- **Image**: Uses official PostgreSQL 15
- **Port Mapping**: Maps container port 5432 to host port 5432
- **Persistent Storage**: Uses a named volume to preserve data between restarts
- **Configuration**: Sets database name, username, and password
- **Health Check**: Verifies database is ready before dependent services start

### 2. Cache (Redis)
```yaml
redis:
  image: redis:alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 5s
    retries: 5
```

- **Image**: Uses lightweight Redis Alpine image
- **Port Mapping**: Maps Redis port to host
- **Persistent Storage**: Preserves cache data between restarts
- **Durability**: Enables AOF persistence with `--appendonly yes` 
- **Health Check**: Ensures Redis is responding before dependent services start

### 3. Backend (FastAPI)
```yaml
backend:
  build: ./backend
  volumes:
    - ./backend:/app
  ports:
    - "8000:8000"
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
  environment:
    - POSTGRES_USER=postgres
    - POSTGRES_PASSWORD=postgres
    - POSTGRES_SERVER=db
    - POSTGRES_PORT=5432
    - POSTGRES_DB=crudapp
    - REDIS_HOST=redis
    - REDIS_PORT=6379
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Build**: Creates image from local Dockerfile
- **Development Mode**: Maps local code directory into container for live changes
- **Port Mapping**: Exposes API on port 8000
- **Dependencies**: Waits for database and Redis to be healthy
- **Configuration**: Provides database and Redis connection details
- **Hot Reload**: Runs uvicorn with `--reload` for development convenience

### 4. Frontend (React + Nginx)
```yaml
frontend:
  build: ./frontend
  volumes:
    - ./frontend:/app
    - /app/node_modules
  ports:
    - "3000:80"
  depends_on:
    - backend
  environment:
    - REACT_APP_API_URL=/api
```

- **Build**: Creates image from local Dockerfile
- **Volumes**: 
  - Maps local code for development
  - Uses anonymous volume for node_modules (prevents overwriting container's modules)
- **Port Mapping**: Maps Nginx's port 80 to host port 3000
- **Dependencies**: Waits for backend to start
- **API Configuration**: Sets backend API URL as "/api" for relative path access

### 5. Persistent Volumes
```yaml
volumes:
  postgres_data:
  redis_data:
```

- **Named Volumes**: Creates persistent storage for both database and cache
- **Data Persistence**: Ensures data survives container restarts and rebuilds

## Data Flow

### Read Operations

1. Client browser makes a request to http://localhost:3000
2. Nginx receives the request and forwards API calls to the backend
3. FastAPI backend first checks Redis cache for the requested data
4. If data is found in cache (cache hit), it's returned immediately
5. If not found (cache miss), the backend retrieves data from PostgreSQL
6. Retrieved data is stored in Redis cache for future requests
7. Data is returned to the frontend and displayed to the user

### Write Operations (Create/Update/Delete)
1. Client submits form data or deletion request
2. Request goes through Nginx to the FastAPI backend
3. Backend validates the incoming data (for creates and updates)
4. Backend performs the operation on the PostgreSQL database
5. Related cache entries are invalidated to ensure data consistency
6. Operation result is returned to the frontend

## Conclusion

This architecture provides a solid foundation for a modern web application with good performance, maintainability, and potential for future growth. The separation of concerns and containerized approach makes it easy to understand, develop, and extend the system as requirements evolve.


