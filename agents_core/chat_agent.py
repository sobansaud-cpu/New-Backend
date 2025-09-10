import os
import google.generativeai as genai
from dotenv import load_dotenv
import base64
from typing import Optional

load_dotenv()

def initialize_gemini():
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    return genai.GenerativeModel('gemini-2.0-flash')

async def generate_chat_response(message: str, image_data: Optional[bytes] = None) -> str:
    """
    Generate a chat response using Gemini AI
    """
    model = initialize_gemini()
    
    try:
        if image_data:
            # Handle image + text input
            image_part = {
                "mime_type": "image/jpeg",  # Assume JPEG for now
                "data": base64.b64encode(image_data).decode()
            }
            
            prompt = f"""
            You are CodeFusion AI, an expert coding assistant. The user has uploaded an image and asked: "{message}"
            
            Please analyze the image and provide helpful insights. You can:
            1. Describe what you see in the image
            2. If it's code/screenshot, help debug or explain it
            3. If it's a design/mockup, suggest how to implement it
            4. If it's an error message, provide solutions
            5. Generate code based on what you see
            
            Be helpful, detailed, and provide actionable advice.
            """
            
            response = await model.generate_content_async([prompt, image_part])
        else:
            # Handle text-only input
            system_prompt = """
            You are CodeFusion AI, an expert coding assistant and creative AI. You help developers with:
            
            1. **Code Generation**: Create websites, apps, APIs in any language/framework
            2. **Code Review**: Analyze and improve existing code
            3. **Debugging**: Find and fix issues in code
            4. **Architecture**: Design system architecture and best practices
            5. **Learning**: Explain programming concepts clearly
            6. **Image Generation**: Create custom images for projects
            
            Always provide:
            - Clear, actionable solutions
            - Code examples when relevant
            - Best practices and explanations
            - Professional, helpful tone
            
            If asked to generate images, provide detailed descriptions of what would be created.
            """
            
            enhanced_prompt = f"{system_prompt}\n\nUser: {message}\n\nCodeFusion AI:"
            response = await model.generate_content_async(enhanced_prompt)
        
        return response.text
        
    except Exception as e:
        print(f"Error generating chat response: {str(e)}")
        return "I apologize, but I'm having trouble processing your request right now. Please try again in a moment."

async def generate_image_response(prompt: str) -> dict:
    """
    Generate an image using AI (placeholder implementation)
    """
    try:
        model = initialize_gemini()

        # For now, we'll provide a detailed description and suggest tools
        # In a real implementation, you would integrate with DALL-E, Midjourney, or Stable Diffusion
        system_prompt = """
        You are CodeFusion AI's image generation assistant. The user wants to generate an image.

        Provide a response that includes:
        1. A detailed description of what the image would look like based on their prompt
        2. Suggested improvements to their prompt for better results
        3. Technical specifications (recommended dimensions, style, etc.)
        4. Alternative approaches or tools they could use

        Format your response as if you're actually generating the image, but explain that this is a description of what would be created.
        """

        enhanced_prompt = f"{system_prompt}\n\nUser wants to generate: {prompt}\n\nResponse:"
        response = await model.generate_content_async(enhanced_prompt)

        # Return both text response and a placeholder image URL
        return {
            "text": response.text,
            "imageUrl": None,  # In real implementation, this would be the generated image URL
            "isImageGeneration": True
        }

    except Exception as e:
        print(f"Error generating image response: {str(e)}")
        return {
            "text": "I apologize, but I'm having trouble with image generation right now. Please try again later.",
            "imageUrl": None,
            "isImageGeneration": True
        }

def analyze_message_intent(message: str) -> str:
    """
    Analyze the user's message to determine intent
    """
    message_lower = message.lower()
    
    if any(keyword in message_lower for keyword in ['generate image', 'create image', 'make image', 'draw', 'picture']):
        return 'image_generation'
    elif any(keyword in message_lower for keyword in ['website', 'web app', 'frontend', 'react', 'vue', 'angular']):
        return 'web_development'
    elif any(keyword in message_lower for keyword in ['api', 'backend', 'server', 'database']):
        return 'backend_development'
    elif any(keyword in message_lower for keyword in ['debug', 'error', 'fix', 'problem', 'issue']):
        return 'debugging'
    elif any(keyword in message_lower for keyword in ['explain', 'how', 'what', 'why', 'learn']):
        return 'learning'
    else:
        return 'general'
