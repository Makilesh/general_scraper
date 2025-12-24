"""
Web Scraper Module - Educational Project
Uses Selenium and BeautifulSoup to scrape publicly available data
IMPORTANT: Only use on sources that permit scraping. Check robots.txt and ToS.
"""

import re
import time
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
from ai_extractor import extract_contacts_with_ai, validate_restaurant_website


def initialize_driver():
    """
    Sets up Chrome WebDriver with options for headless browsing

    Returns:
        WebDriver object configured for scraping
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"Error initializing driver: {e}")
        raise


def is_valid_email(email):
    """
    Validates if an email address is legitimate and not garbage
    
    Parameters:
        email: Email string to validate
    
    Returns:
        Boolean - True if valid business email
    """
    if not email or '@' not in email:
        return False
    
    email = email.lower().strip()
    
    # Must have proper format
    if not re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', email):
        return False
    
    # Reject if too long (likely corrupted data)
    if len(email) > 100:
        return False
    
    # Reject common fake/test domains and aggregator platforms
    invalid_patterns = [
        'example.com', 'domain.com', 'email.com', 'test.com', 'placeholder',
        'yoursite', 'yourdomain', 'sitelock', 'schema.org', 'w3.org',
        'wix.com', 'webpack', 'frontend', 'backend', 'bundle', 'chunk',
        'googletagmanager', 'analytics', '.png', '.jpg', '.jpeg', '.gif',
        'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
        'eazydiner.com', 'zomato.com', 'swiggy.com', 'ubereats.com',
        'doordash.com', 'grubhub.com', 'opentable.com', 'bookatable.com',
        'methodistcollege.com', 'learner', 'enlightsago.com'
    ]
    
    if any(pattern in email for pattern in invalid_patterns):
        return False
    
    # Reject if it looks like a file or code artifact
    if email.count('-') > 3 or email.count('_') > 3:
        return False
    
    # Reject weird patterns that don't look like real emails
    username = email.split('@')[0]
    
    # Reject random-looking usernames with mixed numbers/letters in weird patterns
    if re.search(r'[a-z]{3,}\d+[a-z]{3,}\d+', username):  # like glwithicv123scn456
        return False
    
    # Reject if username has too many dots or numbers in weird places
    if username.count('.') > 2 or (username[0].isdigit() and not username[0:7] in ['contact', 'support', 'info']):
        return False
    
    # Must have valid TLD
    tld = email.split('.')[-1]
    if len(tld) < 2 or not tld.isalpha():
        return False
    
    return True


def search_google_web(search_term):
    """
    Uses Google Search to fetch top 10 website URLs directly
    Enhanced to find actual business websites, not aggregators

    Parameters:
        search_term (string): What to search for (e.g., "restaurants in coimbatore")

    Returns:
        List of website URLs from Google Search results
    """
    driver = None
    try:
        driver = initialize_driver()

        # Construct Google Search URL with better search operators
        # Add "contact" to prioritize pages with contact info
        encoded_term = search_term.replace(' ', '+')
        search_url = f"https://www.google.com/search?q={encoded_term}+contact"

        print(f"Searching Google for: {search_term}")
        driver.get(search_url)
        time.sleep(2)

        # Extract search results
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')

        # Find all search result links
        websites = []
        
        # Google search results are in <a> tags within divs with specific classes
        # Look for actual website links (not Google's internal links)
        search_results = soup.find_all('a', href=True)
        
        # Major aggregator/review sites to exclude
        excluded_domains = [
            'google.com', 'youtube.com', 'facebook.com', 'instagram.com', 
            'twitter.com', 'linkedin.com', 'wikipedia.org', 'maps.google',
            'tripadvisor', 'zomato.com', 'swiggy.com', 'quora.com',
            'yelp.com', 'justdial.com', 'indiamart.com', 'urbanspoon',
            'eater.com', 'timeout.com', 'thrillist.com', 'foursquare.com',
            'pinterest.com', 'reddit.com', 'medium.com', 'blogspot.com',
            'wordpress.com', 'wixsite.com', 'slideshare.net', 'issuu.com',
            'wanderlog.com', 'tripadvisor.in', 'tripadvisor.com',
            'eazydiner.com', 'dineout.co.in', 'opentable.com', 'resy.com',
            'tableagent.com', 'eatigo.com', 'bookatable.com',
            'methodist', 'college', 'university', 'edu', 'school',
            'enlightsago', 'blog', '/blog/', 'news', 'article'
        ]
        
        for result in search_results:
            href = result.get('href', '')
            
            # Extract actual URLs from Google's redirect links
            if '/url?q=' in href:
                # Parse the actual URL
                try:
                    actual_url = href.split('/url?q=')[1].split('&')[0]
                    from urllib.parse import unquote
                    actual_url = unquote(actual_url)
                    
                    # Filter out aggregators and unwanted domains
                    if actual_url.startswith('http') and not any(ex in actual_url.lower() for ex in excluded_domains):
                        websites.append(actual_url)
                except:
                    continue
            
            # Also check for direct links
            elif href.startswith('http') and '/url?' not in href:
                if not any(ex in href.lower() for ex in excluded_domains):
                    websites.append(href)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_websites = []
        for site in websites:
            if site not in seen and len(unique_websites) < 15:  # Get 15 to increase chances
                seen.add(site)
                unique_websites.append(site)
        
        # If we got too many aggregator sites, try a second search with different terms
        if len(unique_websites) < 5:
            print("Not enough direct websites found, trying alternative search...")
            # Try searching for specific business names
            search_url2 = f"https://www.google.com/search?q={encoded_term}+website+email"
            driver.get(search_url2)
            time.sleep(2)
            
            page_source2 = driver.page_source
            soup2 = BeautifulSoup(page_source2, 'lxml')
            
            for result in soup2.find_all('a', href=True):
                href = result.get('href', '')
                
                if '/url?q=' in href:
                    try:
                        actual_url = href.split('/url?q=')[1].split('&')[0]
                        from urllib.parse import unquote
                        actual_url = unquote(actual_url)
                        
                        if actual_url.startswith('http') and not any(ex in actual_url.lower() for ex in excluded_domains):
                            if actual_url not in seen:
                                seen.add(actual_url)
                                unique_websites.append(actual_url)
                                if len(unique_websites) >= 15:
                                    break
                    except:
                        continue
        
        # Take top 10
        unique_websites = unique_websites[:10]
        
        print(f"Found {len(unique_websites)} unique business websites from Google Search")
        for idx, url in enumerate(unique_websites, 1):
            print(f"  [{idx}] {url}")
        
        return unique_websites

    except Exception as e:
        print(f"Error searching Google: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def search_business_directory(search_term):
    """
    Uses Google Maps to fetch business result URLs

    Parameters:
        search_term (string): What to search for (e.g., "restaurants in coimbatore")

    Returns:
        List of URLs containing results
    """
    driver = None
    try:
        driver = initialize_driver()

        # Construct Google Maps search URL
        encoded_term = search_term.replace(' ', '+')
        search_url = f"https://www.google.com/maps/search/{encoded_term}"

        driver.get(search_url)

        # Wait for results to load
        time.sleep(3)

        # Scroll to load more results
        scrollable_div = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
        for _ in range(3):
            driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
            time.sleep(1)

        # Extract business links
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')

        # Find business links (this is a simplified approach)
        links = []
        results = soup.find_all('a', href=re.compile(r'/maps/place/'))

        for result in results[:10]:  # Limit to top 10
            href = result.get('href')
            if href and 'https' not in href:
                full_url = f"https://www.google.com{href}"
                links.append(full_url)
            elif href:
                links.append(href)

        # Remove duplicates
        unique_links = list(set(links))[:10]

        return unique_links

    except Exception as e:
        print(f"Error searching business directory: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def scrape_google_maps_page(url):
    """
    Scrapes Google Maps business page to get business info and website URL

    Parameters:
        url (string): Google Maps URL

    Returns:
        Dictionary with business info from Google Maps
    """
    driver = None
    try:
        driver = initialize_driver()
        driver.get(url)

        # Wait for page to load
        time.sleep(3)

        # Get page source
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')

        # Extract business name
        business_name = None
        try:
            name_element = soup.find('h1')
            if name_element:
                business_name = name_element.get_text(strip=True)
        except:
            pass

        # Extract phone from Google Maps
        phone = None
        try:
            # Look for phone patterns in buttons or divs with aria-label
            phone_pattern = r'(\+91[-\s]?)?[6-9]\d{9}'
            phones = re.findall(phone_pattern, page_source)
            if phones:
                phone = phones[0] if isinstance(phones[0], str) else ''.join(phones[0])
        except:
            pass

        # Extract website URL from Google Maps
        website = None
        try:
            # Look for website link (usually has data-item-id="authority" or similar)
            website_links = soup.find_all('a', href=True)
            for link in website_links:
                href = link.get('href', '')
                # Filter out Google/social media links
                if (href.startswith('http') and 
                    'google.com' not in href and 
                    'facebook.com' not in href and 
                    'instagram.com' not in href and
                    'twitter.com' not in href and
                    'youtube.com' not in href):
                    website = href
                    break
        except:
            pass

        return {
            'business_name': business_name,
            'phone': phone,
            'website': website,
            'maps_url': url
        }

    except Exception as e:
        print(f"Error scraping Google Maps page {url}: {e}")
        return {
            'business_name': None,
            'phone': None,
            'website': None,
            'maps_url': url
        }
    finally:
        if driver:
            driver.quit()


def scrape_with_requests(url):
    """
    Fast lightweight scraping using requests library (no browser needed)
    
    Parameters:
        url: Website URL to scrape
    
    Returns:
        Dictionary with email and phone
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        return extract_contact_info_from_website(response.text, soup)
    
    except Exception as e:
        print(f"    Requests scraping failed: {e}")
        return {'email': None, 'phone': None}


def scrape_single_page(url, driver=None):
    """
    Opens business website URL with Selenium and scrapes for contact info using AI

    Parameters:
        url (string): Business website to scrape
        driver: Optional existing WebDriver instance

    Returns:
        Dictionary with email and additional contact details
    """
    # Try fast method first (requests)
    print(f"  Trying fast scraping for: {url}")
    fast_result = scrape_with_requests(url)
    
    if fast_result.get('email'):
        print(f"  ✓ Email found with fast method: {fast_result['email']}")
        fast_result['website'] = url
        return fast_result
    
    # If fast method didn't find email, use Selenium + AI
    print(f"  Using browser + AI extraction...")
    
    close_driver = False
    if driver is None:
        driver = initialize_driver()
        close_driver = True
    
    try:
        driver.get(url)
        time.sleep(3)
        
        # Scroll to load lazy content
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        except:
            pass
        
        # Get page source after JavaScript rendering
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')
        
        # Get page title
        page_title = soup.find('title')
        page_title_text = page_title.get_text(strip=True) if page_title else ""
        
        # Validate if this is a real restaurant website using AI
        print(f"  Validating website with AI...")
        is_valid_restaurant = validate_restaurant_website(url, page_title_text, page_source[:2000])
        
        if not is_valid_restaurant:
            print(f"  ✗ Not a restaurant website (filtered by AI)")
            return {
                'email': None,
                'phone': None,
                'website': url,
                'is_valid': False
            }
        
        print(f"  ✓ Validated as restaurant website")
        
        # Use AI to extract contact info from main page
        print(f"  Extracting contacts with AI...")
        ai_result = extract_contacts_with_ai(page_source, page_title_text)
        
        contact_info = {
            'email': ai_result.get('email'),
            'phone': ai_result.get('phone'),
            'business_name': ai_result.get('business_name') or page_title_text.split('|')[0].split('-')[0].strip(),
            'website': url,
            'is_valid': True
        }
        
        if contact_info.get('email'):
            print(f"  ✓ AI found email: {contact_info['email']}")
        if contact_info.get('phone'):
            print(f"  ✓ AI found phone: {contact_info['phone']}")
        
        # If AI didn't find anything, try traditional extraction on homepage
        if not contact_info.get('email') or not contact_info.get('phone'):
            print(f"  Trying traditional extraction on homepage...")
            traditional = extract_contact_info_from_website(page_source, soup)
            if traditional.get('email') and not contact_info.get('email'):
                contact_info['email'] = traditional['email']
                print(f"  ✓ Traditional found email: {traditional['email']}")
            if traditional.get('phone') and not contact_info.get('phone'):
                contact_info['phone'] = traditional['phone']
                print(f"  ✓ Traditional found phone: {traditional['phone']}")
        
        # If still no email found, try contact pages
        if not contact_info.get('email'):
            print(f"  No email on homepage, checking contact pages...")
            contact_pages = find_contact_pages(soup, url)
            
            if contact_pages:
                print(f"  Found {len(contact_pages)} potential contact pages")
            
            for idx, contact_url in enumerate(contact_pages[:5], 1):
                try:
                    print(f"    [{idx}] Checking: {contact_url}")
                    driver.get(contact_url)
                    time.sleep(2)
                    
                    # Scroll to load all content
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    
                    contact_page_source = driver.page_source
                    contact_soup = BeautifulSoup(contact_page_source, 'lxml')
                    
                    # Use AI on contact page
                    contact_ai_result = extract_contacts_with_ai(contact_page_source, page_title_text)
                    
                    if contact_ai_result.get('email'):
                        contact_info['email'] = contact_ai_result['email']
                        print(f"    ✓ AI found email: {contact_ai_result['email']}")
                    
                    if contact_ai_result.get('phone'):
                        contact_info['phone'] = contact_ai_result['phone']
                        print(f"    ✓ AI found phone: {contact_ai_result['phone']}")
                    
                    # If AI didn't find anything, try traditional extraction as fallback
                    if not contact_info.get('email') or not contact_info.get('phone'):
                        traditional = extract_contact_info_from_website(contact_page_source, contact_soup)
                        if traditional.get('email') and not contact_info.get('email'):
                            contact_info['email'] = traditional['email']
                            print(f"    ✓ Traditional method found email: {traditional['email']}")
                        if traditional.get('phone') and not contact_info.get('phone'):
                            contact_info['phone'] = traditional['phone']
                            print(f"    ✓ Traditional method found phone: {traditional['phone']}")
                    
                    # Stop if we found both
                    if contact_info.get('email') and contact_info.get('phone'):
                        break
                        
                except Exception as e:
                    print(f"    Error checking contact page: {e}")
                    continue
        
        if not contact_info.get('email'):
            print(f"  ✗ No email found anywhere on {url}")

        return contact_info

    except Exception as e:
        print(f"Error scraping website {url}: {e}")
        return {
            'email': None,
            'phone': None,
            'website': url,
            'is_valid': False
        }
    finally:
        if close_driver and driver:
            driver.quit()


def find_contact_pages(soup, base_url):
    """
    Finds links to contact, about, or other pages that might contain email

    Parameters:
        soup: BeautifulSoup object
        base_url: Base URL of the website

    Returns:
        List of URLs to check
    """
    contact_pages = []
    contact_keywords = ['contact', 'about', 'reach', 'get-in-touch', 'connect', 'support']
    
    try:
        # Parse base URL to get domain
        base_domain = urlparse(base_url).netloc
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '').lower()
            text = link.get_text(strip=True).lower()
            
            # Check if link text or href contains contact keywords
            if any(keyword in href or keyword in text for keyword in contact_keywords):
                # Convert relative URLs to absolute
                full_url = urljoin(base_url, link['href'])
                
                # Only include URLs from same domain
                if urlparse(full_url).netloc == base_domain:
                    contact_pages.append(full_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_pages = []
        for page in contact_pages:
            if page not in seen:
                seen.add(page)
                unique_pages.append(page)
        
        return unique_pages[:3]  # Return max 3 contact pages
    
    except Exception as e:
        print(f"    Error finding contact pages: {e}")
        return []


def extract_contact_info_from_website(page_source, soup=None):
    """
    Enhanced extraction - Uses multiple methods to find emails and phones

    Parameters:
        page_source (string): HTML content of business website
        soup: BeautifulSoup object (optional, will create if not provided)

    Returns:
        Dictionary with contact details
    """
    if soup is None:
        soup = BeautifulSoup(page_source, 'lxml')

    email = None
    phone = None

    # Method 1: Look for mailto: links (most reliable)
    try:
        mailto_links = soup.find_all('a', href=re.compile(r'mailto:', re.I))
        for link in mailto_links:
            href = link.get('href', '')
            email_match = re.search(r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', href, re.I)
            if email_match:
                potential_email = email_match.group(1).lower()
                if is_valid_email(potential_email):
                    email = potential_email
                    break
    except:
        pass

    # Method 2: Look for emails in specific HTML attributes
    if not email:
        try:
            # Check data attributes, aria-labels, etc.
            elements_with_email = soup.find_all(attrs={'data-email': True})
            for elem in elements_with_email:
                potential_email = elem.get('data-email', '')
                if is_valid_email(potential_email):
                    email = potential_email.lower()
                    break
        except:
            pass

    # Method 3: Look in specific elements (footer, contact sections)
    if not email:
        try:
            # Check footer, contact divs, headers, etc.
            contact_sections = soup.find_all(['footer', 'div', 'section', 'header'], 
                                            class_=re.compile(r'(contact|footer|email|info|reach)', re.I))
            for section in contact_sections:
                section_text = section.get_text()
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, section_text, re.I)
                
                valid_emails = [e for e in emails if is_valid_email(e)]
                
                if valid_emails:
                    email = valid_emails[0].lower()
                    break
        except:
            pass

    # Method 4: Look for obfuscated emails (e.g., "info [at] company [dot] com")
    if not email:
        try:
            obfuscated_pattern = r'([A-Za-z0-9._%+-]+)\s*[\[\(]?\s*@\s*[\]\)]?\s*([A-Za-z0-9.-]+)\s*[\[\(]?\s*\.\s*[\]\)]?\s*([A-Za-z]{2,})'
            matches = re.findall(obfuscated_pattern, page_source, re.I)
            if matches:
                potential_email = f"{matches[0][0]}@{matches[0][1]}.{matches[0][2]}".lower()
                if is_valid_email(potential_email):
                    email = potential_email
        except:
            pass

    # Method 5: General page source regex search with better filtering
    if not email:
        try:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, page_source, re.I)
            
            # Filter using validation function
            valid_emails = [e for e in emails if is_valid_email(e)]
            
            # Prefer emails with common business prefixes
            business_prefixes = ['info', 'contact', 'hello', 'support', 'mail', 'inquiry', 'sales', 'admin']
            for e in valid_emails:
                if any(prefix in e.lower() for prefix in business_prefixes):
                    email = e.lower()
                    break
            
            # If no business prefix, take first valid email
            if not email and valid_emails:
                email = valid_emails[0].lower()
        except:
            pass

    # Extract phone number using multiple methods
    try:
        # Method 1: Look for tel: links
        tel_links = soup.find_all('a', href=re.compile(r'tel:', re.I))
        for link in tel_links:
            href = link.get('href', '')
            phone_digits = re.sub(r'\D', '', href)
            if len(phone_digits) >= 10:
                phone = phone_digits
                break
    except:
        pass

    # Method 2: Multiple phone patterns
    if not phone:
        try:
            # Look in contact sections first
            contact_sections = soup.find_all(['footer', 'div', 'section'], 
                                            class_=re.compile(r'(contact|footer|phone|tel|call)', re.I))
            search_text = ' '.join([section.get_text() for section in contact_sections]) if contact_sections else page_source
            
            phone_patterns = [
                r'(\+91[-\s]?)?[6-9]\d{9}',  # Indian mobile
                r'\+91[-.\s]?\d{10}',  # With country code
                r'[6-9]\d{2}[-.\s]?\d{3}[-.\s]?\d{4}',  # With separators
                r'\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
                r'\d{5}[-\s]?\d{5}',  # 10 digits with separator
                r'whatsapp[:\s]+([+\d\s-]+)',  # WhatsApp numbers
            ]
            
            for pattern in phone_patterns:
                phones = re.findall(pattern, search_text)
                if phones:
                    phone_str = phones[0] if isinstance(phones[0], str) else ''.join(phones[0])
                    phone = re.sub(r'\D', '', phone_str)
                    if len(phone) >= 10:
                        break
        except:
            pass

    return {
        'email': email,
        'phone': phone
    }


def scrape_all_results(maps_urls_list):
    """
    Loops through Google Maps URLs, extracts business info and website,
    then scrapes the actual business website for email/phone

    Parameters:
        maps_urls_list (list): List of Google Maps URLs to scrape

    Returns:
        List of dictionaries with complete contact info
    """
    results = []

    for idx, maps_url in enumerate(maps_urls_list, 1):
        print(f"Processing {idx}/{len(maps_urls_list)}: {maps_url}")

        # Step 1: Get business info from Google Maps
        maps_data = scrape_google_maps_page(maps_url)
        
        business_name = maps_data.get('business_name')
        phone_from_maps = maps_data.get('phone')
        website = maps_data.get('website')
        
        print(f"  Business: {business_name}")
        print(f"  Phone from Maps: {phone_from_maps}")
        print(f"  Website: {website}")

        # Step 2: If website exists, scrape it for email and additional contact info
        email = None
        phone_from_website = None
        
        if website:
            try:
                print(f"  Scraping website: {website}")
                website_data = scrape_single_page(website)
                email = website_data.get('email')
                phone_from_website = website_data.get('phone')
                print(f"  Email found: {email}")
                print(f"  Phone from website: {phone_from_website}")
            except Exception as e:
                print(f"  Error scraping website: {e}")

        # Combine data - prefer phone from website, fallback to Maps
        final_phone = phone_from_website or phone_from_maps

        result = {
            'business_name': business_name,
            'email': email,
            'phone': final_phone,
            'website': website,
            'source_url': maps_url
        }
        
        results.append(result)

        # Rate limiting - be respectful
        time.sleep(2)

    return results


def scrape_google_search_results(search_term):
    """
    Uses Google Search with AI validation to find real restaurants and scrape contact info
    
    Parameters:
        search_term (string): Search query (e.g., "restaurants in coimbatore")
    
    Returns:
        List of dictionaries with contact info from validated restaurant websites
    """
    print(f"\n=== GOOGLE SEARCH METHOD WITH AI ===")
    print(f"Searching: {search_term}\n")
    
    # Step 1: Get website URLs from Google Search
    website_urls = search_google_web(search_term)
    
    if not website_urls:
        print("No websites found in Google Search results")
        return []
    
    print(f"\nStarting to scrape {len(website_urls)} websites...\n")
    
    # Step 2: Scrape each website with AI validation
    results = []
    
    for idx, website_url in enumerate(website_urls, 1):
        print(f"[{idx}/{len(website_urls)}] Processing: {website_url}")
        
        try:
            # Scrape with AI-powered extraction
            website_data = scrape_single_page(website_url)
            
            # Skip if AI determined it's not a valid restaurant site
            if website_data.get('is_valid') == False:
                continue
            
            business_name = website_data.get('business_name')
            email = website_data.get('email')
            phone = website_data.get('phone')
            
            # Only add if we have at least name and some contact info
            if business_name and (email or phone):
                if email:
                    print(f"  ✓ Found email: {email}")
                if phone:
                    print(f"  ✓ Found phone: {phone}")
                
                result = {
                    'business_name': business_name,
                    'email': email,
                    'phone': phone,
                    'website': website_url,
                    'source_url': website_url
                }
                
                results.append(result)
            else:
                print(f"  ✗ Insufficient contact info found")
            
            # Rate limiting
            time.sleep(1.5)
            
        except Exception as e:
            print(f"  Error processing {website_url}: {e}")
            continue
    
    print(f"\n=== Completed: {len(results)} valid restaurants found ===\n")
    return results


