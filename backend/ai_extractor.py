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
        # Truncate content to avoid token limits (keep first 8000 chars)
        truncated_content = page_content[:8000] if len(page_content) > 8000 else page_content
        
        prompt = f"""You are a professional data extraction specialist. Extract the business contact information from the following webpage content.

Business Name: {business_name or 'Unknown'}

Webpage Content:
{truncated_content}

Extract and return ONLY the following information in valid JSON format:
{{
    "email": "valid business email or null",
    "phone": "valid phone number or null",
    "business_name": "actual business name from page or null",
    "is_restaurant": true/false
}}

Rules:
- email: Must be a valid business email (not support@, noreply@, or placeholder emails)
- phone: Must be a complete phone number with country code or area code
- business_name: Extract the actual business/restaurant name from the page
- is_restaurant: true only if this is clearly a restaurant/cafe/food business website
- Return null for any field if not found or uncertain
- Do NOT return emails like info@example.com, test@test.com, or any placeholder
- Do NOT return generic Google, Facebook, or social media emails

Return ONLY valid JSON, no additional text."""

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
