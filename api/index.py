"""
Invoice Processing API
Flask-based serverless function for Vercel deployment.
"""

import os
import tempfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from api.processor import extract_invoice_data

# Initialize Flask app
app = Flask(__name__)

# Configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Get OCR API key from environment variable
OCR_API_KEY = os.environ.get('OCR_API_KEY', 'K87899142388957')  # Free demo key

# Known vendors list (can be expanded or loaded from a database)
KNOWN_VENDORS = [
    'Amazon',
    'Walmart',
    'Target',
    'Best Buy',
    'Home Depot',
]


def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension.
    
    Args:
        filename (str): Name of the uploaded file
    
    Returns:
        bool: True if file extension is allowed
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/process', methods=['POST'])
def process_invoice():
    """
    POST endpoint to process invoice images.
    
    Expects:
        - File upload with key 'file'
    
    Returns:
        JSON response with extracted invoice data
    """
    # Check if file is present in request
    if 'file' not in request.files:
        return jsonify({
            'error': 'No file provided',
            'message': 'Please upload a file with key "file"'
        }), 400
    
    file = request.files['file']
    
    # Check if file has a name
    if file.filename == '':
        return jsonify({
            'error': 'Empty filename',
            'message': 'Please select a valid file'
        }), 400
    
    # Validate file extension
    if not allowed_file(file.filename):
        return jsonify({
            'error': 'Invalid file type',
            'message': f'Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    # Process the file
    try:
        # Create a temporary file to save the upload
        filename = secure_filename(file.filename)
        
        # Use tempfile for secure temporary file handling
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            temp_path = temp_file.name
            file.save(temp_path)
        
        # Extract invoice data with OCR API key
        result = extract_invoice_data(temp_path, KNOWN_VENDORS, OCR_API_KEY)
        
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except Exception as cleanup_error:
            print(f"Warning: Failed to delete temp file: {cleanup_error}")
        
        # Check if extraction encountered errors
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error'],
                'data': None
            }), 500
        
        # Return successful response
        return jsonify({
            'success': True,
            'data': {
                'vendor': result['vendor'],
                'date': result['date'],
                'total': result['total']
            }
        }), 200
    
    except Exception as e:
        # Handle unexpected errors
        return jsonify({
            'success': False,
            'error': 'Processing failed',
            'message': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint.
    
    Returns:
        JSON response indicating service status
    """
    return jsonify({
        'status': 'healthy',
        'service': 'Invoice Processing API',
        'version': '1.0.0'
    }), 200


@app.route('/', methods=['GET'])
def index():
    """
    Root endpoint with API information.
    
    Returns:
        JSON response with API usage instructions
    """
    return jsonify({
        'name': 'Intelligent Invoice Processing API',
        'version': '1.0.0',
        'endpoints': {
            '/api/process': {
                'method': 'POST',
                'description': 'Upload invoice image for processing',
                'parameters': {
                    'file': 'Invoice image file (PNG, JPG, PDF, etc.)'
                }
            },
            '/api/health': {
                'method': 'GET',
                'description': 'Health check endpoint'
            }
        }
    }), 200


# For Vercel serverless deployment
# Vercel will automatically detect and use this app
if __name__ == '__main__':
    # This is only used for local development
    app.run(debug=True, host='0.0.0.0', port=5000)
