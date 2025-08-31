"""
Test script for the new Translation Skill (Day 26).
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

from app.services.skills.translation_skill import TranslationSkill
from app.config import Config

async def test_translation_skill():
    """Test the translation skill functionality."""
    print("🌍 Testing Translation Skill (Day 26)")
    print("=" * 50)
    
    # Check if API key is available
    api_key = Config.GOOGLE_TRANSLATE_API_KEY
    if not api_key:
        print("❌ GOOGLE_TRANSLATE_API_KEY not found in environment")
        print("Please add your Google Cloud API key to .env file")
        return
    
    try:
        # Initialize translation skill
        translation_skill = TranslationSkill(api_key)
        print(f"✅ Translation skill initialized: {translation_skill.name}")
        print(f"📝 Description: {translation_skill.description}")
        print(f"🔧 Enabled: {translation_skill.is_enabled()}")
        print()
        
        # Test function definition
        func_def = translation_skill.get_function_definition()
        print("🔧 Function Definition:")
        print(f"   Name: {func_def['name']}")
        print(f"   Description: {func_def['description']}")
        print(f"   Parameters: {list(func_def['parameters']['properties'].keys())}")
        print()
        
        # Test cases
        test_cases = [
            {
                "text": "Hello, how are you?",
                "target_language": "hi",
                "source_language": "en",
                "description": "English to Hindi"
            },
            {
                "text": "Bonjour, comment allez-vous?",
                "target_language": "en",
                "description": "French to English (auto-detect)"
            },
            {
                "text": "こんにちは",
                "target_language": "en",
                "description": "Japanese to English (auto-detect)"
            },
            {
                "text": "Hola mundo",
                "target_language": "de",
                "description": "Spanish to German (auto-detect)"
            }
        ]
        
        print("🧪 Running Translation Tests:")
        print("-" * 30)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test_case['description']}")
            print(f"Input: '{test_case['text']}'")
            
            try:
                # Prepare parameters
                params = {
                    "text": test_case["text"],
                    "target_language": test_case["target_language"]
                }
                
                if "source_language" in test_case:
                    params["source_language"] = test_case["source_language"]
                
                # Execute translation
                result = await translation_skill.execute(**params)
                print(f"✅ Result: {result}")
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        
        print("\n" + "=" * 50)
        print("🏴‍☠️ Translation skill test completed!")
        
    except Exception as e:
        print(f"❌ Failed to initialize translation skill: {str(e)}")
        print("Make sure you have:")
        print("1. Valid Google Cloud API key in .env file")
        print("2. Translation API enabled in Google Cloud Console")
        print("3. Proper authentication configured")

if __name__ == "__main__":
    asyncio.run(test_translation_skill())
