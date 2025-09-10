import os
from typing import List, Dict, Any
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv()

class GeneratedFile(BaseModel):
    path: str
    content: str

class GenerationResult(BaseModel):
    files: List[GeneratedFile]
    success: bool

def initialize_gemini():
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    return genai.GenerativeModel('gemini-2.0-flash')

async def generate_code_with_agent(prompt: str, framework: str, theme: str) -> GenerationResult:
    model = initialize_gemini()
    
    # Determine project type
    frontend_frameworks = ["html", "react", "nextjs", "vue", "angular", "svelte", "nuxt", "gatsby"]
    backend_frameworks = [
        "nodejs-express", "nodejs-nestjs", "python-django", "python-flask", "python-fastapi",
        "php-laravel", "php-codeigniter", "ruby-rails", "ruby-sinatra", "java-spring",
        "csharp-dotnet", "go-gin", "go-echo", "rust-actix", "rust-rocket",
        # Legacy support
        "nodejs", "express", "python", "django", "flask", "fastapi", "go", "java", "php"
    ]
    is_frontend = framework.lower() in frontend_frameworks
    is_backend = framework.lower() in backend_frameworks
    is_fullstack = "fullstack" in framework.lower() or "full stack" in framework.lower()
    
    # Enhanced system prompt for professional website generation
    system_prompt = f"""
    You are an expert AI web developer that generates complete, professional, and production-ready projects based on user prompts.

    FRAMEWORK REQUIREMENT: You MUST use EXACTLY the framework specified: {framework}
    Current theme: {theme}
    Project type: {'Full-stack' if is_fullstack else 'Frontend' if is_frontend else 'Backend'}

    CRITICAL REQUIREMENTS:
    1. Generate COMPLETE, WORKING code for the EXACT framework specified: {framework}
    2. DO NOT use any other framework or technology than what is specified
    3. If user specifies HTML/CSS, generate pure HTML, CSS, and JavaScript - NO React, Vue, or other frameworks
    4. If user specifies React, generate React code - NO HTML/CSS only
    5. If user specifies Vue, generate Vue code - NO React or other frameworks
    6. Include ALL necessary configuration files, dependencies, and setup files for the specified framework
    7. Ensure all code follows best practices and modern standards for the specified framework
    8. Create professional, beautiful, and responsive designs using the specified framework
    9. Include proper error handling and validation appropriate for the framework
    10. Generate realistic and functional content based on the prompt
    11. Ensure all file paths are correct for the specified framework structure
    12. Include proper TypeScript types if applicable to the framework
    13. Add comprehensive styling appropriate for the framework (CSS for HTML, styled-components for React, etc.)
    14. Include proper SEO meta tags and accessibility features appropriate for the framework
    
    Required files for {framework} projects:
    {get_required_files(framework, is_frontend, is_backend, is_fullstack)}
    
    Additional requirements:
    - Include README.md with setup instructions
    - Add proper .gitignore files
    - Include environment variable templates (.env.example)
    - Add proper package.json with all necessary dependencies
    - Include build and development scripts
    - Add proper configuration files (tsconfig.json, vite.config.js, etc.)
    - Include proper routing and navigation
    - Add responsive design and mobile-first approach
    - Include proper error boundaries and loading states
    - Add proper form validation and user feedback
    
    For full-stack projects:
    - Separate frontend and backend clearly
    - Include proper API endpoints
    - Add database schemas and models
    - Include authentication and authorization
    - Add proper error handling and logging
    - Include environment configuration
    - Add proper CORS and security headers
    
    Return files in this exact format:
    file: path/to/file.ext
    ```[file extension]
    [file content here]
    ```
    
    Make sure each file is complete and functional. The generated website should be immediately deployable and professional.
    """
    
    try:
        # Enhanced prompt with specific instructions
        enhanced_user_prompt = f"""
        User Request: {prompt}

        IMPORTANT: You MUST use EXACTLY the framework specified: {framework}

        Please create a professional, complete, and beautiful website that:
        1. Uses ONLY the specified framework: {framework}
        2. Matches the user's requirements exactly using the specified framework
        3. Has a modern, responsive design appropriate for the framework
        4. Includes all necessary functionality using the framework's conventions
        5. Is production-ready and deployable using the framework
        6. Follows current web development best practices for the framework
        7. Has proper error handling and user experience for the framework
        8. Includes realistic content and images
        9. Is optimized for performance and SEO using framework-appropriate methods

        Framework: {framework} (MUST BE USED EXACTLY AS SPECIFIED)
        Theme: {theme}

        Generate a complete, working project with all necessary files for the {framework} framework.
        """
        
        response = await model.generate_content_async(system_prompt + "\n\n" + enhanced_user_prompt)
        files = parse_generated_files(response.text)
        
        # Ensure all required files are present
        files = ensure_framework_requirements(framework, files, is_frontend, is_backend, is_fullstack)
        
        # Add deployment configuration files
        if is_frontend or is_fullstack:
            files = add_deployment_configs(framework, files)
        
        # Add environment configuration
        if is_backend or is_fullstack:
            files = add_environment_configs(framework, files)
        
        # Validate generated files
        files = validate_and_fix_files(framework, files)
        
        return GenerationResult(files=files, success=True)
    except Exception as e:
        print(f"Generation error: {str(e)}")
        return GenerationResult(files=[], success=False)

def get_required_files(framework: str, is_frontend: bool, is_backend: bool, is_fullstack: bool) -> str:
    """Returns comprehensive framework-specific required files"""
    framework = framework.lower()
    
    common_files = {
        "html": """
        - index.html (main entry point with modern HTML5 structure)
        - styles/main.css (comprehensive styling with CSS Grid/Flexbox)
        - scripts/main.js (interactive functionality)
        - assets/ (images, icons, fonts)
        - README.md (setup and usage instructions)
        - .gitignore
        """,
        
        "react": """
        - src/App.jsx (main application component)
        - src/index.jsx (entry point)
        - src/components/ (reusable components)
        - src/pages/ (page components)
        - src/styles/ (CSS modules or styled-components)
        - src/utils/ (helper functions)
        - src/hooks/ (custom React hooks)
        - public/index.html
        - package.json (with all dependencies)
        - tsconfig.json (TypeScript configuration)
        - vite.config.js (Vite configuration)
        - .gitignore
        - README.md
        """,
        
        "nextjs": """
        - src/app/layout.tsx (root layout)
        - src/app/page.tsx (homepage)
        - src/app/globals.css (global styles)
        - src/components/ (reusable components)
        - src/lib/ (utility functions)
        - src/types/ (TypeScript types)
        - public/ (static assets)
        - package.json
        - next.config.js
        - tsconfig.json
        - tailwind.config.js (if using Tailwind)
        - .gitignore
        - README.md
        """,

        "nuxt": """
        - pages/index.vue (homepage)
        - layouts/default.vue (default layout)
        - components/ (reusable components)
        - assets/ (styles, images)
        - static/ (static files)
        - plugins/ (Vue plugins)
        - middleware/ (route middleware)
        - package.json
        - nuxt.config.js
        - .gitignore
        - README.md
        """,

        "gatsby": """
        - src/pages/index.js (homepage)
        - src/components/ (reusable components)
        - src/templates/ (page templates)
        - src/images/ (images)
        - static/ (static files)
        - gatsby-config.js
        - gatsby-node.js
        - package.json
        - .gitignore
        - README.md
        """,
        
        "vue": """
        - src/App.vue (main application)
        - src/main.js (entry point)
        - src/components/ (reusable components)
        - src/views/ (page components)
        - src/router/ (Vue Router configuration)
        - src/store/ (Pinia store)
        - src/assets/ (styles, images)
        - public/index.html
        - package.json
        - vite.config.js
        - .gitignore
        - README.md
        """,
        
        "angular": """
        - src/app/app.component.html (main component)
        - src/app/app.component.ts
        - src/app/app.component.css
        - src/app/app.module.ts
        - src/main.ts (entry point)
        - src/styles.css (global styles)
        - src/app/components/ (reusable components)
        - src/app/pages/ (page components)
        - src/app/services/ (services)
        - angular.json
        - package.json
        - tsconfig.json
        - .gitignore
        - README.md
        """,
        
        "svelte": """
        - src/App.svelte (main application)
        - src/main.js (entry point)
        - src/components/ (reusable components)
        - src/routes/ (page components)
        - src/lib/ (utility functions)
        - src/app.html
        - package.json
        - svelte.config.js
        - vite.config.js
        - .gitignore
        - README.md
        """,
        
        "nodejs": """
        - server.js (main server file)
        - package.json (with all dependencies)
        - .env.example (environment variables template)
        - .gitignore
        - README.md
        """,
        
        "express": """
        - server.js (main server file)
        - routes/ (API route handlers)
        - controllers/ (business logic)
        - middleware/ (custom middleware)
        - models/ (data models)
        - config/ (configuration files)
        - package.json
        - .env.example
        - .gitignore
        - README.md
        """,
        
        "python": """
        - main.py (main application file)
        - requirements.txt (Python dependencies)
        - .env.example (environment variables)
        - .gitignore
        - README.md
        """,
        
        "django": """
        - manage.py (Django management)
        - requirements.txt
        - .env.example
        - .gitignore
        - README.md
        """,
        
        "flask": """
        - app.py (Flask application)
        - requirements.txt
        - .env.example
        - .gitignore
        - README.md
        """,
        
        "fastapi": """
        - main.py (FastAPI application)
        - requirements.txt
        - .env.example
        - .gitignore
        - README.md
        """,
        
        "go": """
        - main.go (main application)
        - go.mod (Go modules)
        - go.sum (Go dependencies)
        - .env.example
        - .gitignore
        - README.md
        """,
        
        "java": """
        - src/main/java/ (Java source files)
        - src/main/resources/ (resources)
        - pom.xml (Maven configuration)
        - .env.example
        - .gitignore
        - README.md
        """,
        
        "php": """
        - index.php (main entry point)
        - composer.json (PHP dependencies)
        - .env.example
        - .gitignore
        - README.md
        """,

        # New backend frameworks
        "nodejs-express": """
        - server.js (Express server)
        - routes/ (API routes)
        - controllers/ (business logic)
        - middleware/ (custom middleware)
        - models/ (data models)
        - config/ (configuration)
        - package.json
        - .env.example
        - .gitignore
        - README.md
        """,

        "nodejs-nestjs": """
        - src/main.ts (NestJS entry point)
        - src/app.module.ts (root module)
        - src/app.controller.ts (main controller)
        - src/app.service.ts (main service)
        - src/modules/ (feature modules)
        - package.json
        - nest-cli.json
        - tsconfig.json
        - .env.example
        - .gitignore
        - README.md
        """,

        "python-django": """
        - manage.py (Django management)
        - myproject/ (project directory)
        - myproject/settings.py (settings)
        - myproject/urls.py (URL configuration)
        - myproject/wsgi.py (WSGI config)
        - myapp/ (Django app)
        - requirements.txt
        - .env.example
        - .gitignore
        - README.md
        """,

        "python-flask": """
        - app.py (Flask application)
        - routes/ (route handlers)
        - models/ (data models)
        - templates/ (Jinja2 templates)
        - static/ (static files)
        - requirements.txt
        - .env.example
        - .gitignore
        - README.md
        """,

        "python-fastapi": """
        - main.py (FastAPI application)
        - routers/ (API routers)
        - models/ (Pydantic models)
        - database/ (database config)
        - requirements.txt
        - .env.example
        - .gitignore
        - README.md
        """,

        "php-laravel": """
        - app/ (application logic)
        - routes/ (route definitions)
        - database/ (migrations, seeders)
        - resources/ (views, assets)
        - config/ (configuration files)
        - composer.json
        - .env.example
        - artisan (Laravel CLI)
        - .gitignore
        - README.md
        """,

        "php-codeigniter": """
        - application/ (MVC structure)
        - system/ (CodeIgniter core)
        - index.php (entry point)
        - composer.json
        - .env.example
        - .gitignore
        - README.md
        """,

        "ruby-rails": """
        - app/ (MVC structure)
        - config/ (configuration)
        - db/ (database files)
        - Gemfile (dependencies)
        - config.ru (Rack config)
        - .env.example
        - .gitignore
        - README.md
        """,

        "ruby-sinatra": """
        - app.rb (Sinatra application)
        - views/ (templates)
        - public/ (static files)
        - Gemfile (dependencies)
        - config.ru (Rack config)
        - .env.example
        - .gitignore
        - README.md
        """,

        "java-spring": """
        - src/main/java/ (Java source)
        - src/main/resources/ (resources)
        - src/test/java/ (tests)
        - pom.xml (Maven config)
        - application.properties
        - .gitignore
        - README.md
        """,

        "csharp-dotnet": """
        - Program.cs (entry point)
        - Controllers/ (API controllers)
        - Models/ (data models)
        - Services/ (business logic)
        - appsettings.json (configuration)
        - .csproj (project file)
        - .gitignore
        - README.md
        """,

        "go-gin": """
        - main.go (entry point)
        - handlers/ (HTTP handlers)
        - models/ (data models)
        - middleware/ (middleware)
        - go.mod (Go modules)
        - go.sum (dependencies)
        - .env.example
        - .gitignore
        - README.md
        """,

        "go-echo": """
        - main.go (entry point)
        - handlers/ (HTTP handlers)
        - models/ (data models)
        - middleware/ (middleware)
        - go.mod (Go modules)
        - go.sum (dependencies)
        - .env.example
        - .gitignore
        - README.md
        """,

        "rust-actix": """
        - src/main.rs (entry point)
        - src/handlers/ (request handlers)
        - src/models/ (data models)
        - Cargo.toml (dependencies)
        - .env.example
        - .gitignore
        - README.md
        """,

        "rust-rocket": """
        - src/main.rs (entry point)
        - src/routes/ (route handlers)
        - src/models/ (data models)
        - Cargo.toml (dependencies)
        - Rocket.toml (Rocket config)
        - .env.example
        - .gitignore
        - README.md
        """
    }
    
    if is_fullstack:
        return """
        FRONTEND:
        - Complete frontend application with all necessary files
        - Modern, responsive design
        - Proper routing and navigation
        - State management
        - API integration
        
        BACKEND:
        - Complete backend API with all endpoints
        - Database models and schemas
        - Authentication and authorization
        - Error handling and validation
        - Environment configuration
        
        DEPLOYMENT:
        - Docker configuration
        - Environment files
        - Build scripts
        - Documentation
        """
    
    return common_files.get(framework, 
        "- Main entry file\n"
        "- Required configuration files\n"
        "- Dependencies and package files\n"
        "- Documentation and setup instructions"
    )

def ensure_framework_requirements(framework: str, files: List[GeneratedFile], is_frontend: bool, is_backend: bool, is_fullstack: bool) -> List[GeneratedFile]:
    """Ensures all framework-specific requirements are met"""
    framework = framework.lower()
    
    # Check if required files exist
    existing_paths = [f.path for f in files]
    
    # Add missing essential files
    if framework in ["react", "nextjs", "vue", "angular", "svelte"] or is_fullstack:
        if not any(f.path == "package.json" for f in files):
            files.append(create_package_json(framework))
        
        if not any(f.path == ".gitignore" for f in files):
            files.append(create_gitignore(framework))
        
        if not any(f.path == "README.md" for f in files):
            files.append(create_readme(framework))
    
    elif framework in ["nodejs", "express"] or is_fullstack:
        if not any(f.path == "package.json" for f in files):
            files.append(create_package_json(framework))
        
        if not any(f.path == ".env.example" for f in files):
            files.append(create_env_example(framework))
    
    elif framework in ["python", "django", "flask", "fastapi"] or is_fullstack:
        if not any(f.path == "requirements.txt" for f in files):
            files.append(create_requirements_txt(framework))
        
        if not any(f.path == ".env.example" for f in files):
            files.append(create_env_example(framework))
    
    elif framework in ["go"] or is_fullstack:
        if not any(f.path == "go.mod" for f in files):
            files.append(create_go_mod(framework))
    
    elif framework in ["java"] or is_fullstack:
        if not any(f.path == "pom.xml" for f in files):
            files.append(create_pom_xml(framework))
    
    elif framework in ["php"] or is_fullstack:
        if not any(f.path == "composer.json" for f in files):
            files.append(create_composer_json(framework))
    
    # Always add README and .gitignore if missing
    if not any(f.path == "README.md" for f in files):
        files.append(create_readme(framework))
    
    if not any(f.path == ".gitignore" for f in files):
        files.append(create_gitignore(framework))
    
    return files

def add_deployment_configs(framework: str, files: List[GeneratedFile]) -> List[GeneratedFile]:
    """Adds deployment configuration files"""
    framework = framework.lower()
    
    # Add Netlify configuration
    if not any(f.path == "netlify.toml" for f in files):
        files.append(create_netlify_config(framework))
    
    # Add Vercel configuration for Next.js
    if framework == "nextjs" and not any(f.path == "vercel.json" for f in files):
        files.append(create_vercel_config())
    
    # Add Docker configuration for full-stack projects
    if not any(f.path == "Dockerfile" for f in files):
        files.append(create_dockerfile(framework))
    
    return files

def add_environment_configs(framework: str, files: List[GeneratedFile]) -> List[GeneratedFile]:
    """Adds environment configuration files"""
    framework = framework.lower()
    
    # Add environment example file
    if not any(f.path == ".env.example" for f in files):
        files.append(create_env_example(framework))
    
    # Add environment validation
    if not any(f.path == "config/env.js" for f in files) and framework in ["nodejs", "express"]:
        files.append(create_env_validation())
    
    return files

def validate_and_fix_files(framework: str, files: List[GeneratedFile]) -> List[GeneratedFile]:
    """Validates and fixes generated files"""
    framework = framework.lower()
    
    # Ensure proper file structure
    for file in files:
        # Fix common path issues
        if file.path.startswith("/"):
            file.path = file.path[1:]
        
        # Ensure proper file extensions
        if framework == "nextjs" and file.path.endswith(".js") and "component" in file.path:
            file.path = file.path.replace(".js", ".tsx")
        
        # Fix package.json content
        if file.path == "package.json":
            try:
                content = json.loads(file.content)
                if "scripts" not in content:
                    content["scripts"] = get_default_scripts(framework)
                if "dependencies" not in content:
                    content["dependencies"] = get_default_dependencies(framework)
                file.content = json.dumps(content, indent=2)
            except:
                pass
    
    return files

def create_package_json(framework: str) -> GeneratedFile:
    """Creates comprehensive package.json for JavaScript frameworks"""
    framework = framework.lower()
    
    base_config = {
        "name": f"generated-{framework}-project",
        "version": "1.0.0",
        "private": True,
        "scripts": get_default_scripts(framework),
        "dependencies": get_default_dependencies(framework),
        "devDependencies": get_default_dev_dependencies(framework),
        "engines": {
            "node": ">=18.0.0",
            "npm": ">=8.0.0"
        }
    }
    
    return GeneratedFile(
        path="package.json",
        content=json.dumps(base_config, indent=2)
    )

def get_default_scripts(framework: str) -> Dict[str, str]:
    """Returns default scripts for different frameworks"""
    scripts = {
        "react": {
            "start": "react-scripts start",
            "build": "react-scripts build",
            "test": "react-scripts test",
            "eject": "react-scripts eject"
        },
        "nextjs": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "lint": "next lint"
        },
        "vue": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview"
        },
        "svelte": {
            "dev": "vite dev",
            "build": "vite build",
            "preview": "vite preview"
        },
        "nodejs": {
            "start": "node server.js",
            "dev": "nodemon server.js"
        },
        "express": {
            "start": "node server.js",
            "dev": "nodemon server.js"
        }
    }
    
    return scripts.get(framework, {
        "dev": "echo 'No dev script'",
        "start": "echo 'No start script'",
        "build": "echo 'No build script'"
    })

def get_default_dependencies(framework: str) -> Dict[str, str]:
    """Returns default dependencies for different frameworks"""
    deps = {
        "react": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "react-router-dom": "^6.8.0"
        },
        "nextjs": {
            "next": "^14.0.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0"
        },
        "vue": {
            "vue": "^3.3.0",
            "vue-router": "^4.2.0",
            "pinia": "^2.1.0"
        },
        "svelte": {
            "svelte": "^4.2.0"
        },
        "nodejs": {
            "express": "^4.18.0",
            "cors": "^2.8.5",
            "dotenv": "^16.0.0"
        },
        "express": {
            "express": "^4.18.0",
            "cors": "^2.8.5",
            "dotenv": "^16.0.0",
            "helmet": "^7.0.0"
        }
    }
    
    return deps.get(framework, {})

def get_default_dev_dependencies(framework: str) -> Dict[str, str]:
    """Returns default dev dependencies for different frameworks"""
    dev_deps = {
        "react": {
            "react-scripts": "^5.0.1"
        },
        "nextjs": {
            "@types/node": "^20.0.0",
            "@types/react": "^18.2.0",
            "@types/react-dom": "^18.2.0",
            "typescript": "^5.0.0"
        },
        "vue": {
            "@vitejs/plugin-vue": "^4.0.0",
            "vite": "^4.0.0"
        },
        "svelte": {
            "@sveltejs/vite-plugin-svelte": "^2.0.0",
            "vite": "^4.0.0"
        },
        "nodejs": {
            "nodemon": "^3.0.0"
        },
        "express": {
            "nodemon": "^3.0.0"
        }
    }
    
    return dev_deps.get(framework, {})

def create_gitignore(framework: str) -> GeneratedFile:
    """Creates comprehensive .gitignore file"""
    content = """
# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Production builds
/build
/dist
/.next
/out

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
logs
*.log

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/

# Dependency directories
jspm_packages/

# Optional npm cache directory
.npm

# Optional REPL history
.node_repl_history

# Output of 'npm pack'
*.tgz

# Yarn Integrity file
.yarn-integrity

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
env.bak/
venv.bak/

# Go
*.exe
*.exe~
*.dll
*.so
*.dylib
*.test
*.out
go.work

# Java
*.class
*.jar
*.war
*.ear
target/
"""
    
    return GeneratedFile(path=".gitignore", content=content.strip())

def create_readme(framework: str) -> GeneratedFile:
    """Creates comprehensive README.md file"""
    framework = framework.lower()
    
    content = f"""# Generated {framework.title()} Project

This project was generated using CodeFusion AI, an advanced AI-powered website builder.

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ (for JavaScript/TypeScript projects)
- Python 3.8+ (for Python projects)
- Go 1.19+ (for Go projects)
- Java 11+ (for Java projects)

### Installation

"""
    
    if framework in ["react", "nextjs", "vue", "svelte", "angular"]:
        content += """```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```
"""
    elif framework in ["nodejs", "express"]:
        content += """```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Start production server
npm start
```
"""
    elif framework in ["python", "django", "flask", "fastapi"]:
        content += """```bash
# Install dependencies
pip install -r requirements.txt

# Start the application
python main.py
```
"""
    elif framework == "go":
        content += """```bash
# Install dependencies
go mod tidy

# Run the application
go run main.go
```
"""
    elif framework == "java":
        content += """```bash
# Build the project
mvn clean install

# Run the application
mvn spring-boot:run
```
"""
    elif framework == "php":
        content += """```bash
# Start PHP server
php -S localhost:8000

# Or use built-in server
php -S localhost:8000 -t public/
```
"""
    
    content += """
## 📁 Project Structure

This project includes all necessary files for a complete, production-ready application.

## 🛠️ Features

- Modern, responsive design
- Professional code structure
- Comprehensive error handling
- Optimized for performance
- SEO-friendly
- Mobile-first approach

## 🚀 Deployment

This project is ready for deployment on:
- Vercel
- Netlify
- Heroku
- AWS
- Google Cloud
- Azure

## 📝 License

This project is generated by CodeFusion AI.

## 🤝 Support

For support and questions, please refer to the CodeFusion AI documentation.
"""
    
    return GeneratedFile(path="README.md", content=content.strip())

def create_env_example(framework: str) -> GeneratedFile:
    """Creates environment variables template"""
    framework = framework.lower()
    
    if framework in ["nodejs", "express"]:
        content = """# Server Configuration
PORT=3000
NODE_ENV=development

# Database Configuration
DATABASE_URL=mongodb://localhost:27017/your_database
# or
DATABASE_URL=postgresql://username:password@localhost:5432/your_database

# Authentication
JWT_SECRET=your_jwt_secret_here
JWT_EXPIRES_IN=7d

# External APIs
API_KEY=your_api_key_here

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password

# File Upload
UPLOAD_PATH=./uploads
MAX_FILE_SIZE=5242880
"""
    elif framework in ["python", "django", "flask", "fastapi"]:
        content = """# Flask/FastAPI Configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your_secret_key_here

# Database Configuration
DATABASE_URL=sqlite:///app.db
# or
DATABASE_URL=postgresql://username:password@localhost:5432/your_database

# Authentication
JWT_SECRET_KEY=your_jwt_secret_here
JWT_ACCESS_TOKEN_EXPIRES=3600

# External APIs
API_KEY=your_api_key_here

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
"""
    elif framework == "go":
        content = """# Go Configuration
PORT=8080
ENV=development

# Database Configuration
DATABASE_URL=postgres://username:password@localhost:5432/your_database

# Authentication
JWT_SECRET=your_jwt_secret_here

# External APIs
API_KEY=your_api_key_here
"""
    elif framework == "java":
        content = """# Java Configuration
SERVER_PORT=8080
SPRING_PROFILES_ACTIVE=development

# Database Configuration
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/your_database
SPRING_DATASOURCE_USERNAME=username
SPRING_DATASOURCE_PASSWORD=password

# JPA Configuration
SPRING_JPA_HIBERNATE_DDL_AUTO=update
SPRING_JPA_SHOW_SQL=true
"""
    else:
        content = """# Environment Variables
# Add your environment variables here
API_KEY=your_api_key_here
DATABASE_URL=your_database_url_here
"""
    
    return GeneratedFile(path=".env.example", content=content.strip())

def create_netlify_config(framework: str) -> GeneratedFile:
    """Creates Netlify configuration file"""
    config = f"""
[build]
  command = "{get_build_command(framework)}"
  publish = "{get_publish_dir(framework)}"
  functions = "functions"

[dev]
  framework = "{get_framework_name(framework)}"
  command = "{get_dev_command(framework)}"
  port = 3000
  targetPort = 3000

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
"""
    
    return GeneratedFile(path="netlify.toml", content=config.strip())

def create_vercel_config() -> GeneratedFile:
    """Creates Vercel configuration file"""
    config = {
        "version": 2,
        "builds": [
            {
                "src": "package.json",
                "use": "@vercel/next"
            }
        ],
        "routes": [
            {
                "handle": "filesystem"
            },
            {
                "src": "/(.*)",
                "dest": "/$1"
            }
        ]
    }
    
    return GeneratedFile(
        path="vercel.json",
        content=json.dumps(config, indent=2)
    )

def create_dockerfile(framework: str) -> GeneratedFile:
    """Creates Docker configuration file"""
    framework = framework.lower()
    
    if framework in ["react", "nextjs", "vue", "svelte"]:
        content = """# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""
    elif framework in ["nodejs", "express"]:
        content = """FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
"""
    elif framework in ["python", "flask", "fastapi"]:
        content = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
"""
    else:
        content = """# Generic Dockerfile
FROM alpine:latest
WORKDIR /app
COPY . .
EXPOSE 8080
CMD ["echo", "Please customize this Dockerfile for your specific framework"]
"""
    
    return GeneratedFile(path="Dockerfile", content=content.strip())

def create_requirements_txt(framework: str) -> GeneratedFile:
    """Creates requirements.txt for Python projects"""
    requirements = {
        "python": [
            "flask==2.3.2",
            "python-dotenv==1.0.0",
            "flask-cors==4.0.0"
        ],
        "django": [
            "django==4.2.0",
            "djangorestframework==3.14.0",
            "python-dotenv==1.0.0"
        ],
        "flask": [
            "flask==2.3.2",
            "flask-cors==4.0.0",
            "python-dotenv==1.0.0",
            "flask-sqlalchemy==3.0.0"
        ],
        "fastapi": [
            "fastapi==0.95.2",
            "uvicorn==0.22.0",
            "python-dotenv==1.0.0",
            "pydantic==1.10.0"
        ]
    }
    
    return GeneratedFile(
        path="requirements.txt",
        content="\n".join(requirements.get(framework, ["flask==2.3.2"]))
    )

def create_go_mod(framework: str) -> GeneratedFile:
    """Creates go.mod for Go projects"""
    content = """module generated-project

go 1.19

require (
    github.com/gin-gonic/gin v1.9.0
    github.com/joho/godotenv v1.4.0
)
"""
    
    return GeneratedFile(path="go.mod", content=content.strip())

def create_pom_xml(framework: str) -> GeneratedFile:
    """Creates pom.xml for Java projects"""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>generated-project</artifactId>
    <version>1.0.0</version>
    
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.0.0</version>
    </parent>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
"""
    
    return GeneratedFile(path="pom.xml", content=content.strip())

def create_composer_json(framework: str) -> GeneratedFile:
    """Creates composer.json for PHP projects"""
    content = """{
    "name": "example/generated-project",
    "description": "Generated PHP project",
    "type": "project",
    "require": {
        "php": ">=8.0",
        "slim/slim": "^4.0",
        "slim/psr7": "^1.5"
    },
    "autoload": {
        "psr-4": {
            "App\\\\": "src/"
        }
    }
}
"""
    
    return GeneratedFile(path="composer.json", content=content.strip())

def create_env_validation() -> GeneratedFile:
    """Creates environment validation for Node.js projects"""
    content = """const Joi = require('joi');

const envSchema = Joi.object({
  NODE_ENV: Joi.string()
    .valid('development', 'production', 'test')
    .default('development'),
  PORT: Joi.number().default(3000),
  DATABASE_URL: Joi.string().required(),
  JWT_SECRET: Joi.string().required(),
  API_KEY: Joi.string().optional(),
}).unknown();

const { error, value: envVars } = envSchema.validate(process.env);

if (error) {
  throw new Error(`Config validation error: ${error.message}`);
}

module.exports = envVars;
"""
    
    return GeneratedFile(path="config/env.js", content=content.strip())

# Helper functions for deployment configuration
def get_build_command(framework: str) -> str:
    framework = framework.lower()
    if framework == "nextjs":
        return "npm run build"
    elif framework == "react":
        return "CI= npm run build"
    elif framework in ["vue", "svelte"]:
        return "npm run build"
    elif framework == "angular":
        return "ng build"
    else:
        return "echo 'No build needed for static site'"

def get_publish_dir(framework: str) -> str:
    framework = framework.lower()
    if framework == "nextjs":
        return ".next"
    elif framework == "react":
        return "build"
    elif framework in ["vue", "svelte"]:
        return "dist"
    elif framework == "angular":
        return "dist"
    else:
        return "."

def get_dev_command(framework: str) -> str:
    framework = framework.lower()
    if framework == "nextjs":
        return "npm run dev"
    elif framework == "react":
        return "npm start"
    elif framework in ["vue", "svelte"]:
        return "npm run dev"
    elif framework == "angular":
        return "ng serve"
    else:
        return "echo 'No dev server needed'"

def get_framework_name(framework: str) -> str:
    framework = framework.lower()
    if framework == "nextjs":
        return "nextjs"
    elif framework == "react":
        return "create-react-app"
    elif framework == "vue":
        return "vue"
    elif framework == "svelte":
        return "svelte"
    elif framework == "angular":
        return "angular"
    else:
        return "static"

def parse_generated_files(text: str) -> List[GeneratedFile]:
    """Enhanced file parsing with better error handling"""
    files = []
    current_file = None
    current_content = ""
    in_code_block = False
    
    for line in text.splitlines():
        if line.startswith("file:"):
            if current_file:
                files.append(GeneratedFile(path=current_file, content=current_content.strip()))
            path = line.split(":", 1)[1].strip()
            current_file = path
            current_content = ""
            in_code_block = False
        elif line.startswith("```") and current_file:
            in_code_block = not in_code_block
        elif current_file and in_code_block:
            current_content += line + "\n"
    
    if current_file:
        files.append(GeneratedFile(path=current_file, content=current_content.strip()))
    
    return files
