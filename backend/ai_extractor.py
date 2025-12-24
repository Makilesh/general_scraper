"""
AI-Powered Contact Extraction Module
Uses OpenAI to intelligently extract and validate business contact information
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def extract_contacts_with_ai(page_content, business_name=None, max_retries=2):
    """
    Uses OpenAI to intelligently extract contact information from webpage content
    
    Parameters:
        page_content (str): HTML or text content from webpage
        business_name (str): Optional business name for context
        max_retries (int): Number of retry attempts
    
    Returns:
        dict: Extracted contact information with validation
    """
    try:
        # Truncate content to avoid token limits (keep first 12000 chars for better coverage)
        truncated_content = page_content[:12000] if len(page_content) > 12000 else page_content
        
        prompt = f"""You are an expert data extraction specialist. Your task is to THOROUGHLY search and extract ALL contact information from this webpage.

Business Name: {business_name or 'Unknown'}

Webpage Content:
{truncated_content}

INSTRUCTIONS:
1. Search EVERYWHERE in the content: header, footer, contact sections, about pages, sidebars
2. Look for emails in: mailto: links, plain text, contact forms, footer text, meta tags
3. Look for phones in: href="tel:", plain text with format +XX, (XXX) XXX-XXXX, or similar
4. Check for obfuscated contacts like: email [at] domain [dot] com
5. Look for WhatsApp numbers, mobile numbers, landline numbers
6. If you see "Contact us" or "Email:" or "Phone:" labels, extract what follows

Extract and return in valid JSON format:
{{
    "email": "best business email found or null",
    "phone": "best phone number found or null",
    "business_name": "actual business name or null",
    "is_restaurant": true/false
}}

RULES:
- email: Return ANY valid business email found (info@, contact@, etc. are acceptable)
- phone: Return ANY valid phone number (with country/area code preferred)
- business_name: Extract from title, h1, or prominent text
- is_restaurant: true if restaurant/cafe/food business
- Return null ONLY if genuinely not found after thorough search
- IGNORE: noreply@, support@wordpress.com, webmaster@, admin@
- IGNORE: Generic template emails like info@example.com, test@test.com

Return ONLY valid JSON, no markdown or extra text."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional data extraction specialist. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean the response (remove markdown code blocks if present)
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        # Parse JSON
        result = json.loads(result_text)
        
        return {
            'email': result.get('email'),
            'phone': result.get('phone'),
            'business_name': result.get('business_name'),
            'is_restaurant': result.get('is_restaurant', False)
        }
        
    except json.JSONDecodeError as e:
        print(f"  ⚠ AI JSON parsing error: {e}")
        return {'email': None, 'phone': None, 'business_name': None, 'is_restaurant': False}
    except Exception as e:
        print(f"  ⚠ AI extraction error: {e}")
        return {'email': None, 'phone': None, 'business_name': None, 'is_restaurant': False}


def validate_restaurant_website(url, page_title, page_content_sample):
    """
    Uses AI to determine if a website is actually a restaurant/food business
    
    Parameters:
        url (str): Website URL
        page_title (str): Page title
        page_content_sample (str): Sample of page content
    
    Returns:
        bool: True if this is a restaurant website
    """
    try:
        prompt = f"""Is this a real restaurant, cafe, or food business website?

URL: {url}
Page Title: {page_title}
Content Sample: {page_content_sample[:1000]}

Answer with only 'yes' or 'no'. Do NOT say yes for:
- Restaurant listing/directory websites (like Zomato, TripAdvisor)
- Food blogs or review sites
- Booking platforms
- Hotel booking sites (unless it's the hotel's own restaurant)
- Educational institutions
- Error pages (403, 404, etc.)

Answer:"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a website classifier. Answer only 'yes' or 'no'."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=10
        )
        
        answer = response.choices[0].message.content.strip().lower()
        return 'yes' in answer
        
    except Exception as e:
        print(f"  ⚠ AI validation error: {e}")
        return False
