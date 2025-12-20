import os
from dotenv import load_dotenv
from src.config.settings import settings

print("Checking environment variables and settings...")
load_dotenv()

print(f"COHERE_API_KEY set: {bool(settings.COHERE_API_KEY)}")
print(f"GEMINI_API_KEY set: {bool(settings.GEMINI_API_KEY)}")
print(f"COHERE_API_KEY first 10 chars: {settings.COHERE_API_KEY[:10] if settings.COHERE_API_KEY else 'Not set'}")
print(f"GEMINI_API_KEY first 10 chars: {settings.GEMINI_API_KEY[:10] if settings.GEMINI_API_KEY else 'Not set'}")

print("\nValidating settings...")
try:
    validation_errors = settings.validate()
    if validation_errors:
        print("Validation errors found:")
        for error in validation_errors:
            print(f"  - {error}")
    else:
        print("All settings are valid!")
except Exception as e:
    print(f"Error validating settings: {e}")