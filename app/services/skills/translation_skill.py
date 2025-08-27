"""
Translation skill using Google Translate API for Captain Blackbeard's Voice Agent.
"""
import httpx
import logging
from typing import Dict, Any
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class TranslationSkill(BaseSkill):
    """Translation skill using Google Translate API."""
    
    def __init__(self, api_key: str):
        """
        Initialize translation skill.
        
        Args:
            api_key: Google Cloud API key with Translation API enabled
        """
        super().__init__(
            name="translation",
            description="Translate text between different languages"
        )
        self.api_key = api_key
        self.base_url = "https://translation.googleapis.com/language/translate/v2"
        
    def get_function_definition(self) -> Dict[str, Any]:
        """Get Gemini function calling definition for translation."""
        return {
            "name": "translate_text",
            "description": "Translate text from one language to another. Supports auto-detection of source language.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to translate"
                    },
                    "target_language": {
                        "type": "string",
                        "description": "Target language code (e.g., 'es' for Spanish, 'fr' for French, 'de' for German, 'ja' for Japanese, 'zh' for Chinese, 'ar' for Arabic, 'hi' for Hindi, 'ru' for Russian, 'it' for Italian, 'pt' for Portuguese)"
                    },
                    "source_language": {
                        "type": "string",
                        "description": "Source language code (optional, will auto-detect if not provided)"
                    }
                },
                "required": ["text", "target_language"]
            }
        }
    
    async def execute(self, text: str, target_language: str, source_language: str = None) -> str:
        """
        Execute translation using Google Translate API.
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (optional)
            
        Returns:
            Formatted translation result
        """
        try:
            logger.info(f"🌍 Translating text to {target_language}")
            
            async with httpx.AsyncClient() as client:
                params = {
                    "key": self.api_key,
                    "q": text,
                    "target": target_language,
                    "format": "text"
                }
                
                # Add source language if provided
                if source_language:
                    params["source"] = source_language
                
                response = await client.post(
                    self.base_url,
                    params=params,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Google Translate API error: {response.status_code}")
                    return f"Arrr! The translation winds be unfavorable, matey. Try again later!"
                
                data = response.json()
                
                if "data" not in data or "translations" not in data["data"]:
                    logger.error("Invalid response format from Google Translate API")
                    return f"Blimey! The translation compass be broken, matey!"
                
                translation_data = data["data"]["translations"][0]
                translated_text = translation_data.get("translatedText", "")
                detected_language = translation_data.get("detectedSourceLanguage", source_language or "unknown")
                
                # Get language names for display
                source_lang_name = self._get_language_name(detected_language)
                target_lang_name = self._get_language_name(target_language)
                
                # Format results with pirate flair
                results = []
                results.append(f"**Original Text ({source_lang_name}):**")
                results.append(f"{text}")
                results.append("")
                results.append(f"**Translation ({target_lang_name}):**")
                results.append(f"{translated_text}")
                
                if not source_language and detected_language:
                    results.append("")
                    results.append(f"*Detected source language: {source_lang_name}*")
                
                prefix = self.get_pirate_response_prefix()
                return f"{prefix}\n\n" + "\n".join(results)
                
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return f"Shiver me timbers! The translation parrot be squawking nonsense: {str(e)}"
    
    def _get_language_name(self, language_code: str) -> str:
        """Get human-readable language name from language code."""
        language_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "ar": "Arabic",
            "hi": "Hindi",
            "th": "Thai",
            "vi": "Vietnamese",
            "nl": "Dutch",
            "sv": "Swedish",
            "da": "Danish",
            "no": "Norwegian",
            "fi": "Finnish",
            "pl": "Polish",
            "cs": "Czech",
            "hu": "Hungarian",
            "ro": "Romanian",
            "bg": "Bulgarian",
            "hr": "Croatian",
            "sk": "Slovak",
            "sl": "Slovenian",
            "et": "Estonian",
            "lv": "Latvian",
            "lt": "Lithuanian",
            "mt": "Maltese",
            "tr": "Turkish",
            "el": "Greek",
            "he": "Hebrew",
            "fa": "Persian",
            "ur": "Urdu",
            "bn": "Bengali",
            "ta": "Tamil",
            "te": "Telugu",
            "ml": "Malayalam",
            "kn": "Kannada",
            "gu": "Gujarati",
            "pa": "Punjabi",
            "mr": "Marathi",
            "ne": "Nepali",
            "si": "Sinhala",
            "my": "Myanmar",
            "km": "Khmer",
            "lo": "Lao",
            "ka": "Georgian",
            "am": "Amharic",
            "sw": "Swahili",
            "zu": "Zulu",
            "af": "Afrikaans",
            "sq": "Albanian",
            "az": "Azerbaijani",
            "be": "Belarusian",
            "bs": "Bosnian",
            "eu": "Basque",
            "gl": "Galician",
            "is": "Icelandic",
            "ga": "Irish",
            "mk": "Macedonian",
            "ms": "Malay",
            "cy": "Welsh",
            "yi": "Yiddish"
        }
        return language_names.get(language_code.lower(), language_code.upper())
