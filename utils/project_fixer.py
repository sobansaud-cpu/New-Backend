import os
import re
from typing import List, Dict

def fix_python_project(project_path: str) -> Dict[str, str]:
    """
    Fix common issues in generated Python projects
    """
    fixes_applied = []
    
    # Check if it's a Python project
    main_py_path = os.path.join(project_path, 'main.py')
    requirements_path = os.path.join(project_path, 'requirements.txt')
    
    if not os.path.exists(main_py_path):
        return {"status": "not_python", "fixes": []}
    
    # Fix 1: Add proper server startup to main.py
    try:
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if it's a FastAPI project
        if 'FastAPI' in content and 'if __name__ == "__main__"' not in content:
            # Add proper startup code
            startup_code = '''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
'''
            content += startup_code
            
            with open(main_py_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            fixes_applied.append("Added uvicorn startup code to main.py")
        
        # Check if it's a Flask project
        elif 'Flask' in content and 'if __name__ == "__main__"' not in content:
            startup_code = '''

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
'''
            content += startup_code
            
            with open(main_py_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            fixes_applied.append("Added Flask startup code to main.py")
            
    except Exception as e:
        fixes_applied.append(f"Error fixing main.py: {str(e)}")
    
    # Fix 2: Ensure requirements.txt has all necessary dependencies
    try:
        if os.path.exists(requirements_path):
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements = f.read().strip().split('\n')
        else:
            requirements = []
        
        # Add missing dependencies based on project type
        with open(main_py_path, 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        required_deps = []
        
        if 'FastAPI' in main_content:
            if 'fastapi' not in [req.lower().split('==')[0] for req in requirements]:
                required_deps.append('fastapi')
            if 'uvicorn' not in [req.lower().split('==')[0] for req in requirements]:
                required_deps.append('uvicorn[standard]')
            if 'pydantic' not in [req.lower().split('==')[0] for req in requirements]:
                required_deps.append('pydantic')
        
        elif 'Flask' in main_content:
            if 'flask' not in [req.lower().split('==')[0] for req in requirements]:
                required_deps.append('flask')
            if 'flask-cors' not in [req.lower().split('==')[0] for req in requirements]:
                required_deps.append('flask-cors')
        
        elif 'Django' in main_content:
            if 'django' not in [req.lower().split('==')[0] for req in requirements]:
                required_deps.append('django')
            if 'djangorestframework' not in [req.lower().split('==')[0] for req in requirements]:
                required_deps.append('djangorestframework')
        
        if required_deps:
            requirements.extend(required_deps)
            with open(requirements_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(requirements))
            fixes_applied.append(f"Added missing dependencies: {', '.join(required_deps)}")
            
    except Exception as e:
        fixes_applied.append(f"Error fixing requirements.txt: {str(e)}")
    
    # Fix 3: Create a startup script
    try:
        startup_script_path = os.path.join(project_path, 'start.py')
        if not os.path.exists(startup_script_path):
            startup_script = '''#!/usr/bin/env python3
"""
Startup script for the generated project
"""
import subprocess
import sys
import os

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def start_server():
    """Start the development server"""
    print("Starting development server...")
    try:
        # Try to run main.py directly first
        subprocess.run([sys.executable, "main.py"])
    except KeyboardInterrupt:
        print("\\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("\\nTrying alternative startup methods...")
        
        # Try uvicorn if it's a FastAPI project
        try:
            subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])
        except Exception:
            print("❌ Could not start with uvicorn either")

if __name__ == "__main__":
    print("🚀 CodeFusion Project Startup")
    print("=" * 40)
    
    # Check if requirements.txt exists
    if os.path.exists("requirements.txt"):
        if install_dependencies():
            start_server()
        else:
            print("❌ Failed to install dependencies. Please install manually:")
            print("   pip install -r requirements.txt")
    else:
        print("⚠️  No requirements.txt found. Starting server directly...")
        start_server()
'''
            
            with open(startup_script_path, 'w', encoding='utf-8') as f:
                f.write(startup_script)
            
            # Make it executable on Unix systems
            try:
                os.chmod(startup_script_path, 0o755)
            except:
                pass  # Windows doesn't support chmod
            
            fixes_applied.append("Created start.py script for easy project startup")
            
    except Exception as e:
        fixes_applied.append(f"Error creating startup script: {str(e)}")
    
    # Fix 4: Create a README with instructions
    try:
        readme_path = os.path.join(project_path, 'README.md')
        if not os.path.exists(readme_path):
            readme_content = '''# Generated Project

This project was generated by CodeFusion AI.

## Quick Start

### Option 1: Use the startup script (Recommended)
```bash
python start.py
```

### Option 2: Manual setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python main.py
   ```

## Project Structure

- `main.py` - Main application file
- `requirements.txt` - Python dependencies
- `start.py` - Automated startup script
- `README.md` - This file

## Development

The server will start on `http://localhost:8000` by default.

For development with auto-reload:
```bash
uvicorn main:app --reload
```

## Deployment

For production deployment, consider using:
- Gunicorn for WSGI applications
- Uvicorn for ASGI applications
- Docker for containerized deployment

## Support

If you encounter any issues, please check:
1. Python version (3.7+ recommended)
2. All dependencies are installed
3. Port 8000 is available

Generated by CodeFusion AI - https://codefusion-ai.com
'''
            
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            fixes_applied.append("Created README.md with setup instructions")
            
    except Exception as e:
        fixes_applied.append(f"Error creating README: {str(e)}")
    
    return {
        "status": "success",
        "fixes": fixes_applied,
        "project_type": "python"
    }

def fix_nodejs_project(project_path: str) -> Dict[str, str]:
    """
    Fix common issues in generated Node.js projects
    """
    fixes_applied = []
    
    package_json_path = os.path.join(project_path, 'package.json')
    
    if not os.path.exists(package_json_path):
        return {"status": "not_nodejs", "fixes": []}
    
    try:
        import json
        
        with open(package_json_path, 'r', encoding='utf-8') as f:
            package_data = json.load(f)
        
        # Fix 1: Ensure proper scripts are present
        if 'scripts' not in package_data:
            package_data['scripts'] = {}
        
        scripts_added = []
        
        # Add start script if missing
        if 'start' not in package_data['scripts']:
            # Check if there's a server.js or index.js
            if os.path.exists(os.path.join(project_path, 'server.js')):
                package_data['scripts']['start'] = 'node server.js'
                scripts_added.append('start')
            elif os.path.exists(os.path.join(project_path, 'index.js')):
                package_data['scripts']['start'] = 'node index.js'
                scripts_added.append('start')
            elif os.path.exists(os.path.join(project_path, 'app.js')):
                package_data['scripts']['start'] = 'node app.js'
                scripts_added.append('start')
        
        # Add dev script if missing
        if 'dev' not in package_data['scripts']:
            if 'start' in package_data['scripts']:
                package_data['scripts']['dev'] = package_data['scripts']['start'].replace('node', 'nodemon')
                scripts_added.append('dev')
        
        if scripts_added:
            with open(package_json_path, 'w', encoding='utf-8') as f:
                json.dump(package_data, f, indent=2)
            fixes_applied.append(f"Added npm scripts: {', '.join(scripts_added)}")
        
        # Fix 2: Add nodemon as dev dependency if not present
        if 'devDependencies' not in package_data:
            package_data['devDependencies'] = {}
        
        if 'nodemon' not in package_data.get('devDependencies', {}):
            package_data['devDependencies']['nodemon'] = '^2.0.0'
            
            with open(package_json_path, 'w', encoding='utf-8') as f:
                json.dump(package_data, f, indent=2)
            fixes_applied.append("Added nodemon as dev dependency")
        
    except Exception as e:
        fixes_applied.append(f"Error fixing package.json: {str(e)}")
    
    return {
        "status": "success", 
        "fixes": fixes_applied,
        "project_type": "nodejs"
    }

def fix_project(project_path: str) -> Dict[str, str]:
    """
    Auto-detect project type and apply appropriate fixes
    """
    if not os.path.exists(project_path):
        return {"status": "error", "fixes": ["Project path does not exist"]}
    
    # Try Python fixes first
    python_result = fix_python_project(project_path)
    if python_result["status"] == "success":
        return python_result
    
    # Try Node.js fixes
    nodejs_result = fix_nodejs_project(project_path)
    if nodejs_result["status"] == "success":
        return nodejs_result
    
    return {"status": "unknown_project_type", "fixes": ["Could not determine project type"]}
