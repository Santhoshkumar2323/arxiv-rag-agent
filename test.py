import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

def ask_gemini(question_text):
    root_dir = Path(__file__).resolve().parent
    env_path = root_dir / 'config' / '.env'
    load_dotenv(dotenv_path=env_path)
    
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = "gemini-2.5-flash"

    if not api_key:
        print(f"❌ Error: GEMINI_API_KEY missing at {env_path}")
        sys.exit(1)
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    try:
        print(f"\n🤖 Asking Gemini: '{question_text}'...")
        response = model.generate_content(question_text)
        print("\n✨ Answer:")
        print(response.text.strip())
    except Exception as e:
        print(f"❌ Failed to get response: {e}")

if __name__ == "__main__":
    user_prompt = "Explain quantum physics to an 8-year-old in two sentences."
    ask_gemini(user_prompt)
