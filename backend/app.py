"""
Flask Backend API - Educational Project
Ties together scraper and data processor
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import scraper
import data_processor
import traceback


def create_app():
    """
    Initializes Flask app with routes and error handlers

    Returns:
        Flask application object
    """
    app = Flask(__name__)
    CORS(app)  # Enable CORS for frontend communication

    # Register error handler
    @app.errorhandler(Exception)
    def handle_error(error):
        return error_handler(error)

    # Register routes
    @app.route('/api/search', methods=['GET', 'POST'])
    def search():
        return route_search()

    @app.route('/api/search-google', methods=['GET', 'POST'])
    def search_google():
        return route_search_google()
    @app.route('/api/status', methods=['GET'])
    def status():
        return route_status()

    @app.route('/', methods=['GET'])
    def home():
        return jsonify({
            'message': 'Web Scraper API - Educational Project',
            'endpoints': {
                '/api/search': 'POST - Search using Google Maps',
                '/api/search-google': 'POST - Search using Google Search (faster)',
                '/api/status': 'GET - Check API status'
            }
        })

    return app


def route_search():
    """
    Calls scraper.py methods, returns structured data

    Parameters:
        search_term (from request body)

    Returns:
        JSON response with contacts
    """
    try:
        # Get search term from request
        if request.method == 'POST':
            data = request.get_json()
            search_term = data.get('search_term', '').strip()
        else:
            search_term = request.args.get('search_term', '').strip()

        # Validate search term
        if not search_term:
            return jsonify({
                'status': 'error',
                'message': 'Search term is required'
            }), 400

        print(f"Searching for: {search_term}")

        # Step 1: Search business directory
        urls = scraper.search_business_directory(search_term)

        if not urls:
            return jsonify({
                'status': 'success',
                'search_term': search_term,
                'results_count': 0,
                'data': [],
                'message': 'No results found for the given search term'
            })

        print(f"Found {len(urls)} URLs")

        # Step 2: Scrape all results
        raw_data = scraper.scrape_all_results(urls)

        print(f"Scraped {len(raw_data)} pages")

        # Step 3: Process and clean data
        response = data_processor.process_scraped_data(raw_data, search_term)

        return jsonify(response)

    except Exception as e:
        print(f"Error in route_search: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def route_search_google():
    """
    NEW: Uses Google Search instead of Google Maps for faster results
    
    Parameters:
        search_term (from request body)
    
    Returns:
        JSON response with contacts from Google Search results
    """
    try:
        # Get search term from request
        if request.method == 'POST':
            data = request.get_json()
            search_term = data.get('search_term', '').strip()
        else:
            search_term = request.args.get('search_term', '').strip()

        # Validate search term
        if not search_term:
            return jsonify({
                'status': 'error',
                'message': 'Search term is required'
            }), 400

        print(f"Google Search method for: {search_term}")

        # Use Google Search scraper
        raw_data = scraper.scrape_google_search_results(search_term)

        if not raw_data:
            return jsonify({
                'status': 'success',
                'search_term': search_term,
                'results_count': 0,
                'data': [],
                'message': 'No results found for the given search term'
            })

        print(f"Scraped {len(raw_data)} websites from Google Search")

        # Process and clean data
        response = data_processor.process_scraped_data(raw_data, search_term)

        return jsonify(response)

    except Exception as e:
        print(f"Error in route_search_google: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def route_status():
    """
    Returns health check and rate limit info

    Returns:
        JSON with scraper status
    """
    return jsonify({
        'status': 'online',
        'service': 'Web Scraper API',
        'version': '1.0.0',
        'educational_purpose': True,
        'message': 'Service is running. Use /api/search to scrape data.'
    })


def error_handler(error):
    """
    Catches exceptions, returns friendly error messages

    Parameters:
        error (Exception object)

    Returns:
        JSON error response
    """
    print(f"Error occurred: {error}")
    traceback.print_exc()

    return jsonify({
        'status': 'error',
        'message': str(error),
        'type': type(error).__name__
    }), 500


def run_app(host='127.0.0.1', port=5000, debug=True):
    """
    Starts Flask development server

    Parameters:
        host (string): Host address
        port (int): Port number
        debug (boolean): Debug mode flag

    Returns:
        None
    """
    app = create_app()
    print(f"Starting Web Scraper API on http://{host}:{port}")
    print("IMPORTANT: This is for educational purposes only.")
    print("Always check robots.txt and Terms of Service before scraping.")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_app()
