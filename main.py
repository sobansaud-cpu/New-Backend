from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os, uuid, subprocess
import json
import sys
import shutil
from typing import Optional
import asyncio
from pathlib import Path
from pydantic import BaseModel
import httpx
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from utils.file_utils import save_project_files, zip_project_files
from utils.github_utils import push_to_github
from utils.project_fixer import fix_project
from agents_core.builder_agent import generate_code_with_agent
from agents_core.fullstack_agent import generate_fullstack_project
from agents_core.chat_agent import generate_chat_response, generate_image_response, analyze_message_intent
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.firestore import SERVER_TIMESTAMP
# from mangum import Mangum


# Load environment variables from .env (for local dev)
load_dotenv()

# Firebase credentials from environment variable (for Vercel/Railway)
import base64

firebase_creds_env = os.getenv("FIREBASE_SERVICE_ACCOUNT")
firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")

try:
    if firebase_creds_env:
        # Try to parse as JSON, or decode if base64
        try:
            # If it's a base64 string, decode it
            if firebase_creds_env.strip().startswith('{'):
                creds_dict = json.loads(firebase_creds_env)
            else:
                creds_json = base64.b64decode(firebase_creds_env).decode('utf-8')
                creds_dict = json.loads(creds_json)
            cred = credentials.Certificate(creds_dict)
        except Exception as e:
            raise Exception(f"Failed to parse FIREBASE_SERVICE_ACCOUNT env variable: {e}")
        firebase_admin.initialize_app(cred, {
            'databaseURL': f'https://{firebase_project_id}.firebaseio.com'
        })
        db = firestore.client()
    else:
        raise Exception('FIREBASE_SERVICE_ACCOUNT env variable not set')
except Exception as e:
    print(f"Error initializing Firebase: {str(e)}")
    raise



app = FastAPI()

# from mangum import Mangum

# Configure CORS
# origins = [
#     "https://a-nother.vercel.app",
#     "http://127.0.0.1:3000",  
#     "http://localhost:8000",
#     "https://sandpack.codesandbox.io",
#     "https://*.netlify.app"  
# ]

origins = [
    # Production
    "https://a-nother.vercel.app",                 # frontend (Vercel)
    "https://another-back-production.up.railway.app",  # backend (Railway)

    # Development / Local Testing
    "http://127.0.0.1:3000",   # local frontend (Next.js)
    "http://localhost:3000",   # local frontend
    "http://localhost:8000",   # local backend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECTS_DIR = "projects"
os.makedirs(PROJECTS_DIR, exist_ok=True)

# Request Models
class GenerateSiteRequest(BaseModel):
    prompt: str
    theme: str
    framework: str
    userId: str
    email: str
    projectType: Optional[str] = "frontend"  # "frontend", "backend", or "fullstack"
    frontendFramework: Optional[str] = None
    backendFramework: Optional[str] = None
    databaseType: Optional[str] = "sqlite"

class PushToGithubRequest(BaseModel):
    projectId: str
    repoName: str
    token: str


class TerminalCommandRequest(BaseModel):
    projectId: str
    command: str

class ProjectModel(BaseModel):
    id: str

class ChatRequest(BaseModel):
    message: str
    userId: str
    conversationId: Optional[str] = None

class ImageChatRequest(BaseModel):
    message: str
    userId: str
    imageData: str  # Base64 encoded image
    conversationId: Optional[str] = None

@app.get("/")
def home():
    return {"message": "🚀 CodeFusion Backend is running"}


 

# main.py - Update the generate endpoint
@app.post("/generate")
async def generate_website(request: Request):
    try:
        data = await request.json()
        prompt = data.get("prompt")
        framework = data.get("framework")
        theme = data.get("theme", "default")
        user_id = data.get("userId")
        email = data.get("email")
        project_id = data.get("projectId")  # New field for editing existing projects
        project_type = data.get("projectType", "frontend")
        frontend_framework = data.get("frontendFramework")
        backend_framework = data.get("backendFramework")
        database_type = data.get("databaseType", "sqlite")
        
        if not prompt:
            return JSONResponse(
                status_code=400,
                content={"error": "Prompt is required"}
            )
        
        if not user_id:
            return JSONResponse(
                status_code=400,
                content={"error": "User ID is required"}
            )
        
        # Check generation limit with transaction
        try:
            can_generate = await check_generation_limit(user_id, email)
            print(f"Generation limit check result for user {user_id}: {can_generate}")
        except Exception as e:
            print(f"Error in check_generation_limit for user {user_id}: {str(e)}")
            # Fallback: allow generation if we can't check the limit
            can_generate = True
            print(f"Fallback: allowing generation due to error")
        
        if not can_generate:
            # Get user's current plan and remaining generations for error message
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            user_data = user_doc.to_dict()
            
            max_count = user_data.get('maxDailyGenerations', 3)
            current_count = user_data.get('dailyGenerations', 0)
            remaining = max_count - current_count
            
            print(f"User {user_id} generation limit details:")
            print(f"  - Plan: {user_data.get('plan')}")
            print(f"  - maxDailyGenerations: {max_count}")
            print(f"  - dailyGenerations: {current_count}")
            print(f"  - remaining: {remaining}")
            print(f"  - firstGenerationDate: {user_data.get('firstGenerationDate')}")
            print(f"  - lastGenerationDate: {user_data.get('lastGenerationDate')}")
            
            error_msg = f"You have reached your daily generation limit ({current_count}/{max_count})"
            
            if user_data.get('plan') == 'free':
                error_msg += ". Upgrade to Pro for 20 generations per day."
                
            return JSONResponse(
                status_code=429,
                content={"error": error_msg}
            )
        
        # If project_id is provided, we're editing an existing project
        if project_id:
            # Verify the project exists and belongs to the user
            project_ref = db.collection('projects').document(project_id)
            project_doc = project_ref.get()
            
            if not project_doc.exists:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Project not found"}
                )
            
            project_data = project_doc.to_dict()
            if project_data.get('userId') != user_id:
                return JSONResponse(
                    status_code=403,
                    content={"error": "You don't have permission to edit this project"}
                )
            
            # Load existing project files
            project_dir = os.path.join(PROJECTS_DIR, project_id)
            if not os.path.exists(project_dir):
                return JSONResponse(
                    status_code=404,
                    content={"error": "Project files not found"}
                )
            
            # Get existing files
            existing_files = []
            for root, _, filenames in os.walk(project_dir):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        existing_files.append({
                            "path": os.path.relpath(file_path, project_dir),
                            "content": content
                        })
                    except UnicodeDecodeError:
                        # Try with different encoding if UTF-8 fails
                        try:
                            with open(file_path, 'r', encoding='latin-1') as f:
                                content = f.read()
                            existing_files.append({
                                "path": os.path.relpath(file_path, project_dir),
                                "content": content
                            })
                        except Exception as e:
                            print(f"Error reading file {file_path}: {str(e)}")
                            # Skip files that can't be read
                            continue
            
            # Generate new content based on existing project context
            existing_prompt = project_data.get('prompt', '')
            enhanced_prompt = f"""Based on this existing project description: "{existing_prompt}"

The project currently has these files:
{chr(10).join([f"- {f['path']}" for f in existing_files[:10]])}

Please add or modify the following: {prompt}

Important instructions:
1. Integrate the new content seamlessly with the existing project structure
2. Maintain consistency with the existing code style and patterns
3. If modifying existing files, preserve their current functionality while adding the new features
4. If creating new files, ensure they work well with the existing project
5. Keep the same framework and technology stack as the original project

Please generate the complete updated files."""
            
            result = await generate_code_with_agent(
                prompt=enhanced_prompt,
                framework=framework,
                theme=theme
            )
            
            # Merge new files with existing files
            new_files = []
            for file_info in result.files:
                new_files.append({
                    "path": file_info.path,
                    "content": file_info.content
                })
            
            # Combine existing and new files, with new files taking precedence
            all_files = existing_files.copy()
            for new_file in new_files:
                # Check if file already exists
                existing_file_index = next(
                    (i for i, f in enumerate(all_files) if f["path"] == new_file["path"]), 
                    None
                )
                if existing_file_index is not None:
                    # Update existing file
                    all_files[existing_file_index] = new_file
                else:
                    # Add new file
                    all_files.append(new_file)
            
            # Save updated files
            save_project_files(project_id, all_files, PROJECTS_DIR)
            
            # Update project in Firestore
            project_ref.update({
                "prompt": f"{project_data.get('prompt', '')}\n\nAdditional: {prompt}",
                "framework": framework,
                "updatedAt": SERVER_TIMESTAMP,
                "files": all_files
            })
            
            await increment_generation_count(user_id)
            
            is_frontend = framework in ["react", "nextjs", "vue", "angular", "html", "svelte"]
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "files": all_files,
                    "projectId": project_id,
                    "language": framework,
                    "isFrontend": is_frontend,
                    "isBackendOnly": framework in ["python", "nodejs", "php", "go", "java"],
                    "isEdit": True
                }
            )
        
        # Handle full-stack project generation
        if project_type == "fullstack" and frontend_framework and backend_framework:
            print(f"Generating full-stack project: {frontend_framework} + {backend_framework} + {database_type}")
            
            result = await generate_fullstack_project(
                prompt=prompt,
                frontend_framework=frontend_framework,
                backend_framework=backend_framework,
                database_type=database_type
            )
            
            if not result.success:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to generate full-stack project"}
                )
            
            # Combine all files from different categories
            all_files = []
            all_files.extend(result.project.frontend_files)
            all_files.extend(result.project.backend_files)
            all_files.extend(result.project.database_files)
            all_files.extend(result.project.deployment_files)
            all_files.extend(result.project.documentation_files)
            
            # Create project ID and save files
            project_id = str(uuid.uuid4())
            save_project_files(project_id, all_files, PROJECTS_DIR)
            
            # Save project to Firestore
            project_ref = db.collection('projects').document(project_id)
            project_ref.set({
                "id": project_id,
                "name": f"Full-Stack Project {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "prompt": prompt,
                "framework": f"{frontend_framework}+{backend_framework}",
                "projectType": "fullstack",
                "frontendFramework": frontend_framework,
                "backendFramework": backend_framework,
                "databaseType": database_type,
                "theme": theme,
                "userId": user_id,
                "createdAt": SERVER_TIMESTAMP,
                "updatedAt": SERVER_TIMESTAMP,
                "files": all_files,
                "setupInstructions": result.setup_instructions,
                "deploymentGuide": result.deployment_guide
            })
            
            await increment_generation_count(user_id)
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "files": all_files,
                    "projectId": project_id,
                    "language": f"{frontend_framework}+{backend_framework}",
                    "isFrontend": True,
                    "isBackendOnly": False,
                    "isFullstack": True,
                    "setupInstructions": result.setup_instructions,
                    "deploymentGuide": result.deployment_guide
                }
            )
        
        # Logic for creating frontend/backend projects
        print(f"Generating {project_type} project with framework: {framework}")
        result = await generate_code_with_agent(
            prompt=prompt,
            framework=framework,
            theme=theme
        )
        
        
        project_id = str(uuid.uuid4())
        files = []
        
        for file_info in result.files:
            files.append({
                "path": file_info.path,
                "content": file_info.content
            })
        
        save_project_files(project_id, files, PROJECTS_DIR)
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        if not os.path.exists(project_dir):
            raise HTTPException(
                status_code=500,
                detail="Failed to save project files"
            )
        print(f"Saved project files to: {project_dir}")
        print(f"Files saved: {os.listdir(project_dir)}")

        # Fix common project issues
        fix_result = fix_project(project_dir)
        print(f"Project fixes applied: {fix_result}")

        # Save project to Firestore
        project_ref = db.collection('projects').document(project_id)
        project_ref.set({
            "id": project_id,
            "name": f"Project {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "prompt": prompt,
            "framework": framework,
            "theme": theme,
            "projectType": "single",
            "userId": user_id,
            "createdAt": SERVER_TIMESTAMP,
            "updatedAt": SERVER_TIMESTAMP,
            "files": files,
            "fixesApplied": fix_result.get("fixes", [])
        })
        
        await increment_generation_count(user_id)
        
        # Determine project characteristics based on project type and framework
        is_frontend = project_type == "frontend" or framework in ["react", "nextjs", "vue", "angular", "html", "svelte", "nuxt", "gatsby"]
        is_backend_only = project_type == "backend" or framework in ["nodejs-express", "nodejs-nestjs", "python-django", "python-flask", "python-fastapi", "php-laravel", "php-codeigniter", "ruby-rails", "ruby-sinatra", "java-spring", "csharp-dotnet", "go-gin", "go-echo", "rust-actix", "rust-rocket"]

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "files": files,
                "projectId": project_id,
                "language": framework,
                "projectType": project_type,
                "isFrontend": is_frontend,
                "isBackendOnly": is_backend_only,
                "isFullstack": project_type == "fullstack"
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/generate-with-image")
async def generate_website_with_image(
    prompt: str = Form(...),
    framework: str = Form(...),
    userId: str = Form(...),
    email: str = Form(...),
    theme: str = Form(default="default"),
    projectType: str = Form(default="single"),
    frontendFramework: Optional[str] = Form(default=None),
    backendFramework: Optional[str] = Form(default=None),
    databaseType: str = Form(default="sqlite"),
    image: UploadFile = File(...)
):
    """
    Generate website with image analysis
    """
    try:
        # Read and encode image
        image_data = await image.read()

        # Enhance prompt with image analysis
        enhanced_prompt = f"""
        {prompt}

        IMPORTANT: An image has been provided for analysis. Please analyze the uploaded image and:
        1. Describe what you see in the image
        2. Use the image as inspiration or reference for the website design
        3. If it's a mockup/design, try to recreate it
        4. If it's content (text, logos, etc.), incorporate it appropriately
        5. Match the style, colors, and layout if applicable

        Create a website that reflects or incorporates elements from the provided image.
        """

        # Use the enhanced prompt for generation
        if projectType == "fullstack":
            result = await generate_fullstack_project(
                prompt=enhanced_prompt,
                frontend_framework=frontendFramework or "react",
                backend_framework=backendFramework or "nodejs",
                database_type=databaseType
            )

            # Process fullstack result
            all_files = []
            for file_info in result.project.frontend_files:
                all_files.append({
                    "path": file_info["path"],
                    "content": file_info["content"]
                })
            for file_info in result.project.backend_files:
                all_files.append({
                    "path": file_info["path"],
                    "content": file_info["content"]
                })
            for file_info in result.project.database_files:
                all_files.append({
                    "path": file_info["path"],
                    "content": file_info["content"]
                })

            project_id = str(uuid.uuid4())
            save_project_files(project_id, all_files, PROJECTS_DIR)

            # Save to Firestore
            project_ref = db.collection('projects').document(project_id)
            project_ref.set({
                "id": project_id,
                "name": f"Project {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "prompt": enhanced_prompt,
                "framework": f"{frontendFramework}+{backendFramework}",
                "theme": theme,
                "projectType": "fullstack",
                "userId": userId,
                "createdAt": SERVER_TIMESTAMP,
                "updatedAt": SERVER_TIMESTAMP,
                "files": all_files,
                "hasImage": True
            })

            await increment_generation_count(userId)

            return JSONResponse({
                "success": True,
                "files": all_files,
                "projectId": project_id,
                "language": f"{frontendFramework}+{backendFramework}",
                "isFrontend": True,
                "isBackendOnly": False,
                "isFullstack": True,
                "setupInstructions": result.setup_instructions,
                "deploymentGuide": result.deployment_guide
            })

        else:
            # Single project generation
            result = await generate_code_with_agent(
                prompt=enhanced_prompt,
                framework=framework,
                theme=theme
            )

            project_id = str(uuid.uuid4())
            files = []

            for file_info in result.files:
                files.append({
                    "path": file_info.path,
                    "content": file_info.content
                })

            save_project_files(project_id, files, PROJECTS_DIR)

            # Save to Firestore
            project_ref = db.collection('projects').document(project_id)
            project_ref.set({
                "id": project_id,
                "name": f"Project {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "prompt": enhanced_prompt,
                "framework": framework,
                "theme": theme,
                "projectType": "single",
                "userId": userId,
                "createdAt": SERVER_TIMESTAMP,
                "updatedAt": SERVER_TIMESTAMP,
                "files": files,
                "hasImage": True
            })

            await increment_generation_count(userId)

            is_frontend = framework in ["react", "nextjs", "vue", "angular", "html", "svelte"]

            return JSONResponse({
                "success": True,
                "files": files,
                "projectId": project_id,
                "language": framework,
                "isFrontend": is_frontend,
                "isBackendOnly": framework in ["python", "nodejs", "php", "go", "java"]
            })

    except Exception as e:
        print(f"Image generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fix-project/{project_id}")
async def fix_project_endpoint(project_id: str):
    """
    Fix common issues in a generated project
    """
    try:
        project_path = os.path.join(PROJECTS_DIR, project_id)

        if not os.path.exists(project_path):
            raise HTTPException(status_code=404, detail="Project not found")

        fix_result = fix_project(project_path)

        # Update project in Firestore with fixes applied
        try:
            project_ref = db.collection('projects').document(project_id)
            project_ref.update({
                "fixesApplied": fix_result.get("fixes", []),
                "lastFixedAt": SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"Error updating project in Firestore: {str(e)}")

        return JSONResponse({
            "success": True,
            "fixes": fix_result.get("fixes", []),
            "projectType": fix_result.get("project_type", "unknown"),
            "message": f"Applied {len(fix_result.get('fixes', []))} fixes to the project"
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"Fix project error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def check_generation_limit(user_id: str, email: str):
    try:
        db = firestore.client()
        user_ref = db.collection('users').document(user_id)
        
        # Use transaction to ensure data consistency
        @firestore.transactional
        def check_limit_transaction(transaction):
            user_doc = user_ref.get(transaction=transaction)
            
            # Create user if doesn't exist
            if not user_doc.exists:
                user_data = {
                    'email': email,
                    'dailyGenerations': 0,
                    'firstGenerationDate': datetime.now().isoformat(),
                    'lastGenerationDate': datetime.now().isoformat(),
                    'maxDailyGenerations': 3,  # Free plan default
                    'plan': 'free',
                    'planExpiry': None
                }
                transaction.set(user_ref, user_data)
                print(f"Created new user {user_id} with free plan")
                return True
            
            user_data = user_doc.to_dict()
            
            # Update maxDailyGenerations based on current plan
            current_plan = user_data.get('plan', 'free')
            if current_plan == 'pro':
                if user_data.get('maxDailyGenerations', 3) != 20:
                    transaction.update(user_ref, {
                        'maxDailyGenerations': 20
                    })
                    user_data['maxDailyGenerations'] = 20
                    print(f"User {user_id} plan updated to pro with 20 generations per day")
            elif current_plan == 'free':
                if user_data.get('maxDailyGenerations', 3) != 3:
                    transaction.update(user_ref, {
                        'maxDailyGenerations': 3
                    })
                    user_data['maxDailyGenerations'] = 3
                    print(f"User {user_id} plan updated to free with 3 generations per day")
            current_time = datetime.now()
            
            # Get the first generation date (when the 24-hour window started)
            # Handle both timezone-aware and timezone-naive datetimes
            first_gen_date_str = user_data.get('firstGenerationDate', user_data.get('lastGenerationDate'))
            if first_gen_date_str:
                try:
                    first_gen_date = datetime.fromisoformat(first_gen_date_str)
                    # If first_gen_date is timezone-aware, make current_time timezone-aware too
                    if first_gen_date.tzinfo is not None:
                        current_time = datetime.now(first_gen_date.tzinfo)
                except ValueError:
                    # Fallback to current time if parsing fails
                    first_gen_date = current_time
            else:
                first_gen_date = current_time
            
            # Check for subscription expiry
            plan_expiry = user_data.get('planExpiry')
            if plan_expiry:
                try:
                    expiry_date = datetime.fromisoformat(plan_expiry)
                    if current_time > expiry_date and user_data.get('plan') == 'pro':
                        # Downgrade to free plan
                        transaction.update(user_ref, {
                            'plan': 'free',
                            'maxDailyGenerations': 3,
                            'planExpiry': None
                        })
                        user_data['plan'] = 'free'
                        user_data['maxDailyGenerations'] = 3
                        print(f"User {user_id} downgraded to free plan due to expiry")
                except ValueError:
                    print(f"Invalid plan expiry date format for user {user_id}")
            
            # Check if 24 hours have passed since the FIRST generation of the day
            # This creates a rolling 24-hour window
            time_since_first = current_time - first_gen_date
            if time_since_first >= timedelta(hours=24):
                # Reset counter and start new 24-hour window
                transaction.update(user_ref, {
                    'dailyGenerations': 0,
                    'firstGenerationDate': current_time.isoformat(),
                    'lastGenerationDate': current_time.isoformat()
                })
                print(f"User {user_id} 24h window reset. New window started at {current_time.isoformat()}")
                return True
            
            # Check if user has generations left
            current_count = user_data.get('dailyGenerations', 0)
            max_count = user_data.get('maxDailyGenerations', 3)
            
            # Fix: Allow generation when current_count is 0 (first generation of the day)
            can_generate = current_count < max_count
            print(f"User {user_id} - Plan: {user_data.get('plan', 'free')}, Current: {current_count}/{max_count}, Can generate: {can_generate}")
            print(f"  - firstGenerationDate: {first_gen_date}")
            print(f"  - time_since_first: {time_since_first}")
            print(f"  - 24h threshold: {timedelta(hours=24)}")
            print(f"  - current_count < max_count: {current_count} < {max_count} = {current_count < max_count}")
            
            return can_generate
        
        # Run the transaction
        try:
            transaction = db.transaction()
            result = check_limit_transaction(transaction)
            print(f"Transaction completed successfully for user {user_id}, result: {result}")
            return result
        except Exception as e:
            print(f"Transaction failed for user {user_id}: {str(e)}")
            # Fallback: check without transaction
            try:
                user_doc = user_ref.get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    current_count = user_data.get('dailyGenerations', 0)
                    max_count = user_data.get('maxDailyGenerations', 3)
                    can_generate = current_count < max_count
                    print(f"Fallback check for user {user_id}: current={current_count}, max={max_count}, can_generate={can_generate}")
                    return can_generate
                else:
                    print(f"User {user_id} not found in fallback check")
                    return True  # Allow generation for new users
            except Exception as fallback_error:
                print(f"Fallback check also failed for user {user_id}: {str(fallback_error)}")
                return True  # Allow generation if all checks fail
        
    except Exception as e:
        print(f"Error checking generation limit: {str(e)}")
        return False

async def increment_generation_count(user_id: str):
    try:
        db = firestore.client()
        user_ref = db.collection('users').document(user_id)
        
        # Use transaction to prevent race conditions
        @firestore.transactional
        def increment_transaction(transaction):
            user_doc = user_ref.get(transaction=transaction)
            user_data = user_doc.to_dict()
            
            # Get current time for this transaction
            current_time = datetime.now()
            
            # Get the first generation date (when the 24-hour window started)
            # Handle both timezone-aware and timezone-naive datetimes
            first_gen_date_str = user_data.get('firstGenerationDate', user_data.get('lastGenerationDate'))
            if first_gen_date_str:
                try:
                    first_gen_date = datetime.fromisoformat(first_gen_date_str)
                    # If first_gen_date is timezone-aware, make current_time timezone-aware too
                    if first_gen_date.tzinfo is not None:
                        current_time = datetime.now(first_gen_date.tzinfo)
                except ValueError:
                    # Fallback to current time if parsing fails
                    first_gen_date = current_time
            else:
                first_gen_date = current_time
            
            # If 24 hours passed since first generation, start new window
            time_since_first = current_time - first_gen_date
            if time_since_first >= timedelta(hours=24):
                transaction.update(user_ref, {
                    'dailyGenerations': 1,
                    'firstGenerationDate': current_time.isoformat(),
                    'lastGenerationDate': current_time.isoformat()
                })
                print(f"User {user_id} - New 24h window started. Count reset to 1")
            else:
                # Otherwise increment count and update last generation date
                current_count = user_data.get('dailyGenerations', 0)
                new_count = current_count + 1
                transaction.update(user_ref, {
                    'dailyGenerations': firestore.Increment(1),
                    'lastGenerationDate': current_time.isoformat()
                })
                print(f"User {user_id} - Generation count incremented to {new_count}")
        
        transaction = db.transaction()
        increment_transaction(transaction)
        
    except Exception as e:
        print(f"Error incrementing generation count: {str(e)}")
        raise
    

async def migrate_existing_users():
    """Migrate existing users to include firstGenerationDate field"""
    try:
        db = firestore.client()
        users_ref = db.collection('users')
        users = users_ref.stream()
        
        for user_doc in users:
            user_data = user_doc.to_dict()
            
            # Check if user already has firstGenerationDate
            if 'firstGenerationDate' not in user_data:
                # Set firstGenerationDate to lastGenerationDate if it exists, otherwise to now
                first_gen_date = user_data.get('lastGenerationDate', datetime.now().isoformat())
                
                user_ref = db.collection('users').document(user_doc.id)
                user_ref.update({
                    'firstGenerationDate': first_gen_date
                })
                print(f"Migrated user {user_doc.id} with firstGenerationDate: {first_gen_date}")
        
        print("Migration completed successfully")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")

# Add this to your startup code or create an endpoint to run it
# await migrate_existing_users()

@app.get("/simple-check/{user_id}")
async def simple_user_check(user_id: str):
    """Simple user check without transactions for debugging"""
    try:
        db = firestore.client()
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return JSONResponse(
                status_code=404,
                content={"error": "User not found"}
            )
        
        user_data = user_doc.to_dict()
        current_count = user_data.get('dailyGenerations', 0)
        max_count = user_data.get('maxDailyGenerations', 3)
        can_generate = current_count < max_count
        
        simple_check = {
            "userId": user_id,
            "email": user_data.get('email'),
            "plan": user_data.get('plan'),
            "maxDailyGenerations": max_count,
            "dailyGenerations": current_count,
            "canGenerate": can_generate,
            "remainingGenerations": max(0, max_count - current_count),
            "firstGenerationDate": user_data.get('firstGenerationDate'),
            "lastGenerationDate": user_data.get('lastGenerationDate')
        }
        
        return JSONResponse(content=simple_check)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Simple check failed: {str(e)}"}
        )

@app.get("/debug/user/{user_id}")
async def debug_user_status(user_id: str):
    """Debug endpoint to check user's generation status"""
    try:
        db = firestore.client()
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return JSONResponse(
                status_code=404,
                content={"error": "User not found"}
            )
        
        user_data = user_doc.to_dict()
        now = datetime.now()
        
        # Get the first generation date
        first_gen_date_str = user_data.get('firstGenerationDate', user_data.get('lastGenerationDate'))
        first_gen_date = None
        if first_gen_date_str:
            try:
                first_gen_date = datetime.fromisoformat(first_gen_date_str)
            except ValueError:
                first_gen_date = now
        else:
            first_gen_date = now
        
        # Calculate time since first generation
        time_since_first = None
        if first_gen_date:
            time_since_first = now - first_gen_date
        
        debug_info = {
            "userId": user_id,
            "email": user_data.get('email'),
            "plan": user_data.get('plan'),
            "maxDailyGenerations": user_data.get('maxDailyGenerations'),
            "dailyGenerations": user_data.get('dailyGenerations'),
            "firstGenerationDate": first_gen_date_str,
            "lastGenerationDate": user_data.get('lastGenerationDate'),
            "planExpiry": user_data.get('planExpiry'),
            "currentTime": now.isoformat(),
            "timeSinceFirstGeneration": str(time_since_first) if time_since_first else None,
            "canGenerate": user_data.get('dailyGenerations', 0) < user_data.get('maxDailyGenerations', 3),
            "remainingGenerations": max(0, user_data.get('maxDailyGenerations', 3) - user_data.get('dailyGenerations', 0))
        }
        
        return JSONResponse(content=debug_info)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Debug failed: {str(e)}"}
        )

@app.post("/migrate-users")
async def run_migration():
    """Run migration for existing users"""
    try:
        await migrate_existing_users()
        return JSONResponse(
            status_code=200,
            content={"message": "Migration completed successfully"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Migration failed: {str(e)}"}
        )




@app.get("/projects/{user_id}")
async def get_user_projects(user_id: str):
    try:
        projects_ref = db.collection('projects').where('userId', '==', user_id)
        docs = projects_ref.stream()  # Changed from get() to stream()
        
        projects = []
        for doc in docs:
            project = doc.to_dict()
            # Convert timestamps
            if 'createdAt' in project:
                project['createdAt'] = project['createdAt'].isoformat()
            if 'updatedAt' in project:
                project['updatedAt'] = project['updatedAt'].isoformat()
                
            projects.append({
                "id": project["id"],
                "name": project["name"],
                "prompt": project["prompt"],
                "framework": project["framework"],
                "createdAt": project.get("createdAt"),
                "updatedAt": project.get("updatedAt")
            })
            
        return {"projects": projects}
    except Exception as e:
        print(f"Error getting user projects: {str(e)}")  # Add logging
        raise HTTPException(status_code=500, detail=str(e))
    
    
@app.get("/project/{project_id}")
async def get_project(project_id: str):
    try:
        project_ref = db.collection('projects').document(project_id)
        project_doc = project_ref.get()  # Remove await
        
        if not project_doc.exists:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Convert Firestore document to dict and handle timestamps
        project_data = project_doc.to_dict()
        
        # Convert Firestore timestamps to ISO strings
        if 'createdAt' in project_data:
            project_data['createdAt'] = project_data['createdAt'].isoformat()
        if 'updatedAt' in project_data:
            project_data['updatedAt'] = project_data['updatedAt'].isoformat()
        
        return project_data
        
    except Exception as e:
        print(f"Error getting project: {str(e)}")  # Add logging
        raise HTTPException(status_code=500, detail=str(e))
    
@app.delete("/project/{project_id}")
async def delete_project(project_id: str):
    try:
        # Delete from Firestore
        db.collection('projects').document(project_id).delete()  # Remove await
        
        # Delete project files
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        if os.path.exists(project_dir):
            import shutil
            shutil.rmtree(project_dir)
            
        return {"success": True}
    except Exception as e:
        print(f"Error deleting project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/project/{project_id}")
async def update_project(project_id: str, request: Request):
    try:
        data = await request.json()
        
        # Verify the project exists and belongs to the user
        project_ref = db.collection('projects').document(project_id)
        project_doc = project_ref.get()
        
        if not project_doc.exists:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_data = project_doc.to_dict()
        user_id = data.get("userId")
        
        if project_data.get('userId') != user_id:
            raise HTTPException(status_code=403, detail="You don't have permission to update this project")
        
        # Update project data
        update_data = {
            "name": data.get("name", project_data.get("name")),
            "prompt": data.get("prompt", project_data.get("prompt")),
            "framework": data.get("framework", project_data.get("framework")),
            "updatedAt": SERVER_TIMESTAMP
        }
        
        # If files are provided, update them too
        if "files" in data:
            update_data["files"] = data["files"]
            # Also save files to disk
            save_project_files(project_id, data["files"], PROJECTS_DIR)
        
        project_ref.update(update_data)
        
        return {"success": True, "message": "Project updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/download/{project_id}")
async def download_project(project_id: str):
    try:
        zip_path = zip_project_files(project_id, PROJECTS_DIR)
        if not os.path.exists(zip_path):
            raise HTTPException(status_code=404, detail="Project not found")
        return FileResponse(zip_path, filename=f"{project_id}.zip")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/github/push")
async def github_push(data: PushToGithubRequest):
    try:
        if not (
            (data.token.startswith("ghp_") and len(data.token) == 40) or
            (data.token.startswith("github_pat_") and len(data.token) >= 60)
        ):
            raise ValueError("Invalid GitHub token format")

        result = push_to_github(data.projectId, data.repoName, data.token)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/terminal/execute")
async def execute_terminal_command(data: TerminalCommandRequest):
    try:
        project_dir = os.path.join(PROJECTS_DIR, data.projectId)
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail="Project not found")
        
        process = await asyncio.create_subprocess_shell(
            data.command,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "success": True,
            "output": stdout.decode(),
            "error": stderr.decode(),
            "return_code": process.returncode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/project/{project_id}/files")
async def get_project_files(project_id: str):
    try:
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail="Project not found")
        
        files = []
        for root, _, filenames in os.walk(project_dir):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                with open(file_path, 'r') as f:
                    content = f.read()
                files.append({
                    "path": os.path.relpath(file_path, project_dir),
                    "content": content
                })
        
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/preview/{project_id}")
async def get_frontend_preview(project_id: str):
    try:
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        
        # Verify project exists in Firestore first
        project_ref = db.collection('projects').document(project_id)
        project_doc = project_ref.get()
        
        if not project_doc.exists:
            raise HTTPException(status_code=404, detail="Project not found in database")
            
        if not os.path.exists(project_dir):
            raise HTTPException(
                status_code=404, 
                detail=f"Project files not found at {project_dir}"
            )
        
        project_data = project_doc.to_dict()
        framework = project_data.get('framework', '').lower()
        
        # Handle different frameworks
        if framework in ['nextjs', 'react', 'vue', 'angular', 'svelte']:
            # For modern frameworks, try to build and serve
            try:
                # Check if build directory exists
                build_dirs = {
                    'nextjs': '.next',
                    'react': 'build',
                    'vue': 'dist',
                    'angular': 'dist',
                    'svelte': 'dist'
                }
                
                build_dir = build_dirs.get(framework, 'build')
                build_path = os.path.join(project_dir, build_dir)
                
                if os.path.exists(build_path):
                    # Look for index.html in build directory
                    html_files = [
                        f for f in os.listdir(build_path) 
                        if f.lower().endswith('.html')
                    ]
                    
                    if html_files:
                        html_file = html_files[0]
                        with open(os.path.join(build_path, html_file), 'r') as f:
                            content = f.read()
                        return HTMLResponse(content=content)
                
                # If no build directory, try to build the project
                if framework == 'nextjs':
                    # For Next.js, create a simple preview
                    return HTMLResponse(content=f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Next.js Project Preview</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; }}
                            .container {{ max-width: 800px; margin: 0 auto; }}
                            .build-btn {{ 
                                background: #0070f3; color: white; padding: 12px 24px; 
                                border: none; border-radius: 6px; cursor: pointer; 
                                font-size: 16px; margin: 20px 0;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>Next.js Project Preview</h1>
                            <p>This is a Next.js project. To view the full preview, you need to build it first.</p>
                            <button class="build-btn" onclick="buildProject()">Build Project</button>
                            <div id="status"></div>
                        </div>
                        <script>
                            async function buildProject() {{
                                const status = document.getElementById('status');
                                status.innerHTML = 'Building project... This may take a few minutes.';
                                
                                try {{
                                    const response = await fetch('/api/build-project', {{
                                        method: 'POST',
                                        headers: {{ 'Content-Type': 'application/json' }},
                                        body: JSON.stringify({{ projectId: '{project_id}' }})
                                    }});
                                    
                                    if (response.ok) {{
                                        status.innerHTML = 'Build completed! Refreshing...';
                                        setTimeout(() => location.reload(), 2000);
                                    }} else {{
                                        status.innerHTML = 'Build failed. Please try again.';
                                    }}
                                }} catch (error) {{
                                    status.innerHTML = 'Build error: ' + error.message;
                                }}
                            }}
                        </script>
                    </body>
                    </html>
                    """)
                
                # For other frameworks, try to find HTML files in root
                html_files = [
                    f for f in os.listdir(project_dir) 
                    if f.lower().endswith('.html')
                ]
                
                if html_files:
                    html_file = html_files[0]
                    with open(os.path.join(project_dir, html_file), 'r') as f:
                        content = f.read()
                    return HTMLResponse(content=content)
                
            except Exception as e:
                print(f"Error building {framework} project: {str(e)}")
        
        # Fallback: look for HTML files in project root
        html_files = [
            f for f in os.listdir(project_dir) 
            if f.lower().endswith('.html')
        ]
        
        if not html_files:
            # Try to find index.html specifically
            possible_files = ['index.html', 'main.html', 'app.html']
            html_files = [
                f for f in possible_files
                if os.path.exists(os.path.join(project_dir, f))
            ]
            
            if not html_files:
                return HTMLResponse(
                    content=f"<h1>No HTML file found in this {framework} project</h1><p>This project uses {framework} framework and needs to be built first.</p>", 
                    status_code=404
                )
        
        # Try each HTML file until we find one that works
        for html_file in html_files:
            try:
                with open(os.path.join(project_dir, html_file), 'r') as f:
                    content = f.read()
                return HTMLResponse(content=content)
            except Exception as e:
                print(f"Error reading {html_file}: {str(e)}")
                continue
        
        return HTMLResponse(
            content="<h1>Could not read any HTML files</h1>",
            status_code=500
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Preview error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build-project")
async def build_project(request: Request):
    """Build a project for preview"""
    try:
        data = await request.json()
        project_id = data.get("projectId")
        
        if not project_id:
            raise HTTPException(status_code=400, detail="Project ID is required")
        
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get project info from Firestore
        project_ref = db.collection('projects').document(project_id)
        project_doc = project_ref.get()
        
        if not project_doc.exists:
            raise HTTPException(status_code=404, detail="Project not found in database")
        
        project_data = project_doc.to_dict()
        framework = project_data.get('framework', '').lower()
        
        # Build commands for different frameworks
        build_commands = {
            'nextjs': ['npm', 'install', '&&', 'npm', 'run', 'build'],
            'react': ['npm', 'install', '&&', 'npm', 'run', 'build'],
            'vue': ['npm', 'install', '&&', 'npm', 'run', 'build'],
            'angular': ['npm', 'install', '&&', 'ng', 'build'],
            'svelte': ['npm', 'install', '&&', 'npm', 'run', 'build']
        }
        
        if framework not in build_commands:
            raise HTTPException(status_code=400, detail=f"Building {framework} projects is not supported")
        
        # Run build command
        build_cmd = ' '.join(build_commands[framework])
        print(f"Building {framework} project: {build_cmd}")
        
        process = await asyncio.create_subprocess_shell(
            build_cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            print(f"Build failed: {stderr.decode()}")
            raise HTTPException(
                status_code=500, 
                detail=f"Build failed: {stderr.decode()}"
            )
        
        print(f"Build successful: {stdout.decode()}")

        return JSONResponse({
            "success": True,
            "message": "Project built successfully",
            "output": stdout.decode()
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"Build error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """
    Chat endpoint for CodeFusion AI assistant
    """
    try:
        # Analyze message intent
        intent = analyze_message_intent(request.message)

        # Generate response based on intent
        if intent == 'image_generation':
            image_result = await generate_image_response(request.message)
            response = image_result["text"]
            image_url = image_result.get("imageUrl")
        else:
            response = await generate_chat_response(request.message)
            image_url = None

        # Save conversation to Firebase (optional)
        if request.conversationId:
            try:
                conversation_ref = db.collection('conversations').document(request.conversationId)
                conversation_ref.collection('messages').add({
                    'role': 'user',
                    'content': request.message,
                    'timestamp': SERVER_TIMESTAMP,
                    'userId': request.userId
                })
                conversation_ref.collection('messages').add({
                    'role': 'assistant',
                    'content': response,
                    'timestamp': SERVER_TIMESTAMP,
                    'intent': intent
                })
            except Exception as e:
                print(f"Error saving conversation: {str(e)}")

        return JSONResponse({
            "success": True,
            "response": response,
            "intent": intent,
            "imageUrl": image_url if intent == 'image_generation' else None
        })

    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/image")
async def chat_with_image(request: ImageChatRequest):
    """
    Chat endpoint with image upload for CodeFusion AI assistant
    """
    try:
        import base64

        # Decode base64 image
        image_data = base64.b64decode(request.imageData)

        # Generate response with image analysis
        response = await generate_chat_response(request.message, image_data)

        # Save conversation to Firebase (optional)
        if request.conversationId:
            try:
                conversation_ref = db.collection('conversations').document(request.conversationId)
                conversation_ref.collection('messages').add({
                    'role': 'user',
                    'content': request.message,
                    'hasImage': True,
                    'timestamp': SERVER_TIMESTAMP,
                    'userId': request.userId
                })
                conversation_ref.collection('messages').add({
                    'role': 'assistant',
                    'content': response,
                    'timestamp': SERVER_TIMESTAMP,
                    'intent': 'image_analysis'
                })
            except Exception as e:
                print(f"Error saving conversation: {str(e)}")

        return JSONResponse({
            "success": True,
            "response": response,
            "intent": "image_analysis"
        })

    except Exception as e:
        print(f"Image chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# handler = Mangum(app)