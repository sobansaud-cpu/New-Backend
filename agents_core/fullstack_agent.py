import os
from typing import List, Dict, Any
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv()

class FullstackProject(BaseModel):
    frontend_files: List[Dict[str, str]]
    backend_files: List[Dict[str, str]]
    database_files: List[Dict[str, str]]
    deployment_files: List[Dict[str, str]]
    documentation_files: List[Dict[str, str]]

class FullstackGenerationResult(BaseModel):
    success: bool
    project: FullstackProject
    setup_instructions: str
    deployment_guide: str

def initialize_gemini():
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    return genai.GenerativeModel('gemini-2.0-flash')

async def generate_fullstack_project(prompt: str, frontend_framework: str, backend_framework: str, database_type: str = "sqlite") -> FullstackGenerationResult:
    """
    Generate a complete full-stack project with frontend, backend, and database integration
    """
    model = initialize_gemini()
    
    system_prompt = f"""
    You are an expert full-stack developer specializing in creating production-ready, professional web applications.
    
    FRONTEND FRAMEWORK: {frontend_framework}
    BACKEND FRAMEWORK: {backend_framework}
    DATABASE: {database_type}
    
    CRITICAL REQUIREMENTS:
    1. Create a COMPLETE, WORKING full-stack application
    2. Frontend and backend must be properly integrated
    3. Include proper API endpoints and data flow
    4. Add comprehensive error handling and validation
    5. Include proper authentication and authorization
    6. Add database models and schemas
    7. Include proper CORS and security headers
    8. Add comprehensive testing setup
    9. Include proper deployment configurations
    10. Add detailed documentation and setup instructions
    
    PROJECT STRUCTURE:
    - Frontend: Complete {frontend_framework} application with routing, state management, and UI components
    - Backend: Complete {backend_framework} API with proper architecture
    - Database: {database_type} setup with models and migrations
    - Integration: Proper API communication between frontend and backend
    - Security: Authentication, authorization, input validation
    - Testing: Unit tests, integration tests, API tests
    - Deployment: Docker, environment configs, CI/CD setup
    
    RESPONSE FORMAT:
    You must respond with files in this exact format:
    
    file:frontend/src/App.jsx
    ```jsx
    // Your React component code here
    ```
    
    file:backend/app.py
    ```python
    # Your Python backend code here
    ```
    
    file:database/schema.sql
    ```sql
    -- Your database schema here
    ```
    
    Continue with all necessary files. Each file must start with "file:" followed by the path, then a code block.
    
    Return the complete project structure with all necessary files.
    """
    
    try:
        # Enhanced user prompt for full-stack generation
        enhanced_prompt = f"""
        User Request: {prompt}
        
        Please create a professional, complete full-stack web application that:
        1. Has a beautiful, responsive frontend using {frontend_framework}
        2. Includes a robust backend API using {backend_framework}
        3. Integrates with {database_type} database
        4. Has proper user authentication and authorization
        5. Includes comprehensive error handling and validation
        6. Is production-ready and deployable
        7. Follows current web development best practices
        8. Has proper security measures
        9. Includes comprehensive testing
        10. Has detailed documentation
        
        The application should be immediately functional and demonstrate proper full-stack architecture.
        """
        
        response = await model.generate_content_async(system_prompt + "\n\n" + enhanced_prompt)
        
        # Parse the response and create project structure
        project = parse_fullstack_response(response.text, frontend_framework, backend_framework, database_type)
        
        # Generate setup and deployment instructions
        setup_instructions = generate_setup_instructions(frontend_framework, backend_framework, database_type)
        deployment_guide = generate_deployment_guide(frontend_framework, backend_framework, database_type)
        
        return FullstackGenerationResult(
            success=True,
            project=project,
            setup_instructions=setup_instructions,
            deployment_guide=deployment_guide
        )
        
    except Exception as e:
        print(f"Full-stack generation error: {str(e)}")
        return FullstackGenerationResult(
            success=False,
            project=FullstackProject(
                frontend_files=[],
                backend_files=[],
                database_files=[],
                deployment_files=[],
                documentation_files=[]
            ),
            setup_instructions="",
            deployment_guide=""
        )

def parse_fullstack_response(response_text: str, frontend_framework: str, backend_framework: str, database_type: str) -> FullstackProject:
    """
    Parse the AI response and organize files by category
    """
    # This is a simplified parser - in production, you'd want more sophisticated parsing
    lines = response_text.split('\n')
    
    frontend_files = []
    backend_files = []
    database_files = []
    deployment_files = []
    documentation_files = []
    
    current_file = None
    current_content = ""
    in_code_block = False
    
    for line in lines:
        if line.startswith("file:"):
            if current_file:
                # Categorize the file based on path and content
                file_data = {"path": current_file, "content": current_content.strip()}
                categorize_file(file_data, frontend_files, backend_files, database_files, deployment_files, documentation_files)
            
            path = line.split(":", 1)[1].strip()
            current_file = path
            current_content = ""
            in_code_block = False
            
        elif line.startswith("```") and current_file:
            in_code_block = not in_code_block
            
        elif current_file and in_code_block:
            current_content += line + "\n"
    
    # Don't forget the last file
    if current_file:
        file_data = {"path": current_file, "content": current_content.strip()}
        categorize_file(file_data, frontend_files, backend_files, database_files, deployment_files, documentation_files)
    
    # Ensure essential files are present
    ensure_essential_files(frontend_files, backend_files, database_files, deployment_files, documentation_files, 
                          frontend_framework, backend_framework, database_type)
    
    return FullstackProject(
        frontend_files=frontend_files,
        backend_files=backend_files,
        database_files=database_files,
        deployment_files=deployment_files,
        documentation_files=documentation_files
    )

def categorize_file(file_data: Dict[str, str], frontend_files: List, backend_files: List, database_files: List, 
                   deployment_files: List, documentation_files: List):
    """
    Categorize a file based on its path and content
    """
    path = file_data["path"].lower()
    
    # Frontend files
    if any(ext in path for ext in ['.html', '.jsx', '.tsx', '.vue', '.svelte', '.css', '.scss', '.sass']):
        frontend_files.append(file_data)
    # Backend files
    elif any(ext in path for ext in ['.py', '.js', '.ts', '.go', '.java', '.php']):
        backend_files.append(file_data)
    # Database files
    elif any(ext in path for ext in ['.sql', '.db', '.sqlite', 'schema', 'migration']):
        database_files.append(file_data)
    # Deployment files
    elif any(ext in path for ext in ['dockerfile', 'docker-compose', '.yml', '.yaml', 'vercel.json', 'netlify.toml']):
        deployment_files.append(file_data)
    # Documentation files
    elif any(ext in path for ext in ['.md', 'readme', 'docs', 'api']):
        documentation_files.append(file_data)
    # Default to backend for unknown file types
    else:
        backend_files.append(file_data)

def ensure_essential_files(frontend_files: List, backend_files: List, database_files: List, 
                          deployment_files: List, documentation_files: List,
                          frontend_framework: str, backend_framework: str, database_type: str):
    """
    Ensure all essential files are present for a full-stack project
    """
    # Add missing essential files
    add_missing_frontend_files(frontend_files, frontend_framework)
    add_missing_backend_files(backend_files, backend_framework)
    add_missing_database_files(database_files, database_type)
    add_missing_deployment_files(deployment_files, frontend_framework, backend_framework)
    add_missing_documentation_files(documentation_files, frontend_framework, backend_framework, database_type)

def add_missing_frontend_files(frontend_files: List, framework: str):
    """Add missing essential frontend files"""
    existing_paths = [f["path"] for f in frontend_files]
    
    if framework == "react" and "package.json" not in existing_paths:
        frontend_files.append({
            "path": "package.json",
            "content": create_react_package_json()
        })
    
    if framework == "nextjs" and "next.config.js" not in existing_paths:
        frontend_files.append({
            "path": "next.config.js",
            "content": create_nextjs_config()
        })
    
    if framework == "vue" and "vite.config.js" not in existing_paths:
        frontend_files.append({
            "path": "vite.config.js",
            "content": create_vue_vite_config()
        })

def add_missing_backend_files(backend_files: List, framework: str):
    """Add missing essential backend files"""
    existing_paths = [f["path"] for f in backend_files]
    
    if framework == "nodejs" and "package.json" not in existing_paths:
        backend_files.append({
            "path": "package.json",
            "content": create_nodejs_package_json()
        })
    
    if framework == "python" and "requirements.txt" not in existing_paths:
        backend_files.append({
            "path": "requirements.txt",
            "content": create_python_requirements()
        })
    
    if framework == "go" and "go.mod" not in existing_paths:
        backend_files.append({
            "path": "go.mod",
            "content": create_go_mod()
        })

def add_missing_database_files(database_files: List, database_type: str):
    """Add missing essential database files"""
    existing_paths = [f["path"] for f in database_files]
    
    if database_type == "sqlite" and "database/schema.sql" not in existing_paths:
        database_files.append({
            "path": "database/schema.sql",
            "content": create_sqlite_schema()
        })
    
    if database_type == "postgresql" and "database/migrations" not in existing_paths:
        database_files.append({
            "path": "database/migrations/001_initial.sql",
            "content": create_postgres_migration()
        })

def add_missing_deployment_files(deployment_files: List, frontend_framework: str, backend_framework: str):
    """Add missing essential deployment files"""
    existing_paths = [f["path"] for f in deployment_files]
    
    if "Dockerfile" not in existing_paths:
        deployment_files.append({
            "path": "Dockerfile",
            "content": create_dockerfile(frontend_framework, backend_framework)
        })
    
    if "docker-compose.yml" not in existing_paths:
        deployment_files.append({
            "path": "docker-compose.yml",
            "content": create_docker_compose(frontend_framework, backend_framework)
        })
    
    if frontend_framework in ["react", "nextjs", "vue"] and ".env.example" not in existing_paths:
        deployment_files.append({
            "path": ".env.example",
            "content": create_env_example(frontend_framework, backend_framework)
        })

def add_missing_documentation_files(documentation_files: List, frontend_framework: str, backend_framework: str, database_type: str):
    """Add missing essential documentation files"""
    existing_paths = [f["path"] for f in documentation_files]
    
    if "README.md" not in existing_paths:
        documentation_files.append({
            "path": "README.md",
            "content": create_fullstack_readme(frontend_framework, backend_framework, database_type)
        })
    
    if "API.md" not in existing_paths:
        documentation_files.append({
            "path": "API.md",
            "content": create_api_documentation()
        })

# File creation functions
def create_react_package_json() -> str:
    return json.dumps({
        "name": "fullstack-app-frontend",
        "version": "1.0.0",
        "private": True,
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "react-router-dom": "^6.8.0",
            "axios": "^1.3.0",
            "react-query": "^3.39.0"
        },
        "scripts": {
            "start": "react-scripts start",
            "build": "react-scripts build",
            "test": "react-scripts test",
            "eject": "react-scripts eject"
        },
        "devDependencies": {
            "react-scripts": "^5.0.1"
        }
    }, indent=2)

def create_nextjs_config() -> str:
    return """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;"""

def create_vue_vite_config() -> str:
    return """import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})"""

def create_nodejs_package_json() -> str:
    return json.dumps({
        "name": "fullstack-app-backend",
        "version": "1.0.0",
        "main": "server.js",
        "scripts": {
            "start": "node server.js",
            "dev": "nodemon server.js",
            "test": "jest"
        },
        "dependencies": {
            "express": "^4.18.2",
            "cors": "^2.8.5",
            "helmet": "^7.0.0",
            "dotenv": "^16.0.0",
            "bcryptjs": "^2.4.3",
            "jsonwebtoken": "^9.0.0",
            "sqlite3": "^5.1.6"
        },
        "devDependencies": {
            "nodemon": "^2.0.20",
            "jest": "^29.0.0"
        }
    }, indent=2)

def create_python_requirements() -> str:
    return """fastapi==0.95.2
uvicorn==0.22.0
sqlalchemy==2.0.0
alembic==1.10.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
sqlite3
pytest==7.3.1"""

def create_go_mod() -> str:
    return """module fullstack-app

go 1.19

require (
    github.com/gin-gonic/gin v1.9.0
    github.com/mattn/go-sqlite3 v1.14.16
    github.com/golang-jwt/jwt/v4 v4.5.0
    golang.org/x/crypto v0.9.0
)"""

def create_sqlite_schema() -> str:
    return """-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Posts table
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);"""

def create_postgres_migration() -> str:
    return """-- Migration: 001_initial
-- Up
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Down
-- DROP TABLE posts;
-- DROP TABLE users;"""

def create_dockerfile(frontend_framework: str, backend_framework: str) -> str:
    return f"""# Multi-stage build for full-stack application
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production
COPY frontend/ .
RUN npm run build

FROM python:3.11-slim AS backend-builder
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .

FROM nginx:alpine
COPY --from=frontend-builder /app/frontend/build /usr/share/nginx/html
COPY --from=backend-builder /app/backend /app/backend
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]"""

def create_docker_compose(frontend_framework: str, backend_framework: str) -> str:
    return """version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile
      target: frontend-builder
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    depends_on:
      - backend

  backend:
    build:
      context: .
      dockerfile: Dockerfile
      target: backend-builder
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./app.db
    volumes:
      - ./data:/app/data

  database:
    image: sqlite:latest
    volumes:
      - ./data:/data
    ports:
      - "5432:5432"

volumes:
  data:"""

def create_env_example(frontend_framework: str, backend_framework: str) -> str:
    return """# Frontend Environment Variables
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development

# Backend Environment Variables
PORT=8000
NODE_ENV=development
DATABASE_URL=sqlite:///./app.db
JWT_SECRET=your_jwt_secret_here
JWT_EXPIRES_IN=7d

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fullstack_app
DB_USER=postgres
DB_PASSWORD=password

# Security
CORS_ORIGIN=http://localhost:3000
RATE_LIMIT_WINDOW=15
RATE_LIMIT_MAX_REQUESTS=100"""

def create_fullstack_readme(frontend_framework: str, backend_framework: str, database_type: str) -> str:
    return f"""# Full-Stack Web Application

This is a complete, production-ready full-stack web application built with modern technologies.

## 🏗️ Architecture

- **Frontend**: {frontend_framework.title()}
- **Backend**: {backend_framework.title()}
- **Database**: {database_type.title()}
- **Authentication**: JWT-based
- **API**: RESTful with proper error handling

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.8+ (for Python backend)
- Go 1.19+ (for Go backend)
- {database_type.title()} database

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

### Backend Setup
```bash
cd backend
# For Node.js
npm install
npm run dev

# For Python
pip install -r requirements.txt
python main.py

# For Go
go mod tidy
go run main.go
```

### Database Setup
```bash
# The database will be automatically created on first run
# For PostgreSQL, create a database and update .env file
```

## 📁 Project Structure

```
├── frontend/          # {frontend_framework.title()} application
├── backend/           # {backend_framework.title()} API
├── database/          # Database schemas and migrations
├── docs/             # Documentation
└── deployment/       # Docker and deployment configs
```

## 🔧 Features

- ✅ User authentication and authorization
- ✅ RESTful API with proper error handling
- ✅ Database integration with {database_type}
- ✅ Responsive frontend design
- ✅ Comprehensive testing setup
- ✅ Docker containerization
- ✅ Environment configuration
- ✅ Security best practices

## 🧪 Testing

```bash
# Frontend tests
cd frontend
npm test

# Backend tests
cd backend
npm test  # or pytest for Python
```

## 🚀 Deployment

### Docker
```bash
docker-compose up --build
```

### Manual Deployment
1. Build frontend: `npm run build`
2. Start backend server
3. Configure reverse proxy (nginx)
4. Set environment variables

## 📚 API Documentation

See [API.md](API.md) for detailed API documentation.

## 🔒 Security

- JWT authentication
- Password hashing with bcrypt
- CORS configuration
- Input validation and sanitization
- Rate limiting
- Security headers

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
"""

def create_api_documentation() -> str:
    return """# API Documentation

## Authentication

### POST /api/auth/register
Register a new user.

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "number",
    "username": "string",
    "email": "string"
  },
  "token": "string"
}
```

### POST /api/auth/login
Login user.

**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "number",
    "username": "string",
    "email": "string"
  },
  "token": "string"
}
```

## Posts

### GET /api/posts
Get all posts.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "posts": [
    {
      "id": "number",
      "title": "string",
      "content": "string",
      "user_id": "number",
      "created_at": "string"
    }
  ]
}
```

### POST /api/posts
Create a new post.

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "title": "string",
  "content": "string"
}
```

**Response:**
```json
{
  "success": true,
  "post": {
    "id": "number",
    "title": "string",
    "content": "string",
    "user_id": "number",
    "created_at": "string"
  }
}
```

## Error Handling

All API endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

## Status Codes

- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

## Rate Limiting

API requests are limited to 100 requests per 15-minute window per IP address.
"""

def generate_setup_instructions(frontend_framework: str, backend_framework: str, database_type: str) -> str:
    """Generate comprehensive setup instructions"""
    return f"""
# Setup Instructions

## 1. Clone and Install Dependencies

### Frontend ({frontend_framework})
```bash
cd frontend
npm install
```

### Backend ({backend_framework})
```bash
cd backend
# For Node.js
npm install

# For Python
pip install -r requirements.txt

# For Go
go mod tidy
```

## 2. Environment Configuration

Copy `.env.example` to `.env` and configure:
- Database connection strings
- JWT secrets
- API URLs
- CORS origins

## 3. Database Setup

### {database_type.title()}
```bash
# The database will be created automatically
# For PostgreSQL, create database first
createdb fullstack_app
```

## 4. Start Development Servers

### Frontend
```bash
cd frontend
npm start
# Runs on http://localhost:3000
```

### Backend
```bash
cd backend
# Node.js
npm run dev

# Python
python main.py

# Go
go run main.go
# Runs on http://localhost:8000
```

## 5. Verify Installation

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/health
- Database: Check connection in backend logs
"""

def generate_deployment_guide(frontend_framework: str, backend_framework: str, database_type: str) -> str:
    """Generate comprehensive deployment guide"""
    return f"""
# Deployment Guide

## Docker Deployment (Recommended)

### 1. Build and Run
```bash
docker-compose up --build
```

### 2. Production Environment
```bash
# Set production environment variables
export NODE_ENV=production
export DATABASE_URL=your_production_db_url

docker-compose -f docker-compose.prod.yml up --build
```

## Manual Deployment

### 1. Frontend Build
```bash
cd frontend
npm run build
# Copy build/ folder to web server
```

### 2. Backend Deployment
```bash
cd backend
# Install production dependencies
npm ci --only=production

# Start production server
npm start
```

### 3. Reverse Proxy (Nginx)
```nginx
server {{
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {{
        root /var/www/frontend;
        try_files $uri $uri/ /index.html;
    }}

    # Backend API
    location /api {{
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
```

## Environment Variables

### Production
```bash
NODE_ENV=production
DATABASE_URL=your_production_db_url
JWT_SECRET=your_secure_jwt_secret
CORS_ORIGIN=https://yourdomain.com
```

## Database Migration

### {database_type.title()}
```bash
# For SQLite: No migration needed
# For PostgreSQL: Run migrations
cd backend
npm run migrate
```

## SSL/HTTPS

### Let's Encrypt
```bash
sudo certbot --nginx -d yourdomain.com
```

## Monitoring

### Health Checks
- Frontend: `/health`
- Backend: `/api/health`
- Database: Connection test

### Logs
```bash
# Docker logs
docker-compose logs -f

# Application logs
tail -f /var/log/app.log
```

## Backup

### Database
```bash
# SQLite
cp app.db backup/app.db.$(date +%Y%m%d)

# PostgreSQL
pg_dump fullstack_app > backup/app_$(date +%Y%m%d).sql
```
"""
