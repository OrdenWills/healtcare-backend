from flask import Flask, request, jsonify,send_from_directory
import os
import requests
from flask_cors import CORS
import json
import html
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app,resources={r"/api/*": {"origins": "https://healthcare-translator-wn42.vercel.app/"}})  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# For production, get these from environment variables
LIBRETRANSLATE_URL = os.getenv('LIBRETRANSLATE_URL', 'https://libretranslate.com')
API_KEY = os.getenv('API_KEY', '')  # Optional API key for LibreTranslate

# Map language codes from Web Speech API to LibreTranslate
def map_language_code(code):
    # Map from "en-US" format to "en" format
    return code.split('-')[0]

def translate_chunked_text(text, source_lang, target_lang, api_key, email=None):
    # Split text into chunks of ~450 bytes to stay under the 500 byte limit
    # Note: This is a simple approach. For more accurate chunking by sentence,
    # consider using nltk or similar libraries
    chunk_size = 450
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    translated_chunks = []
    
    for chunk in chunks:
        url = "https://api.mymemory.translated.net/get"
        params = {
            'q': chunk,
            'langpair': f"{source_lang}|{target_lang}",
            'key': api_key,
        }
        
        if email:
            params['de'] = email
            
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            if 'responseData' in result and 'translatedText' in result['responseData']:
                translated_chunks.append(result['responseData']['translatedText'])
            else:
                raise Exception(result.get('responseDetails', 'Unknown translation error'))
        else:
            raise Exception(f"Translation service error: {response.status_code}")
    
    return " ".join(translated_chunks)

@app.route('/api/translate', methods=['POST'])
def translate():
    try:
        data = request.json
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text']
        source_lang = map_language_code(data.get('sourceLanguage', 'en-US'))
        target_lang = map_language_code(data.get('targetLanguage', 'es-ES'))
        
        # API key from environment variables
        api_key = os.getenv('MYMEMORY_API_KEY', '')
        email = os.getenv('CONTACT_EMAIL', '')
        
        # Use the chunked translation function for longer texts
        translated_text = translate_chunked_text(
            text, source_lang, target_lang, api_key, email)
        
        # Sanitize output to prevent XSS
        translated_text = html.escape(translated_text)
        
        return jsonify({
            'translatedText': translated_text,
            'sourceLang': source_lang,
            'targetLang': target_lang
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Use environment variable for port if available (for hosting platforms)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)