import os
import zipfile
from pathlib import Path

def save_project_files(project_id: str, files: list, base_dir: str):
    try:
        project_dir = os.path.join(base_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        for file in files:
            file_path = os.path.join(project_dir, file['path'])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file['content'])
                
        return True
    except Exception as e:
        print(f"Error saving files: {str(e)}")
        raise  

def zip_project_files(project_id: str, base_dir: str = "projects") -> str:
    """Create a zip archive of the project files"""
    zip_path = Path(base_dir) / f"{project_id}.zip"
    project_dir = Path(base_dir) / project_id
    
    if not project_dir.exists():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in project_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(project_dir)
                zipf.write(file, arcname)
    
    return str(zip_path)