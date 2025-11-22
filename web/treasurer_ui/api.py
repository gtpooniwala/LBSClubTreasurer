"""
Flask API Backend for Treasurer Dashboard
Serves data from CSV files
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
import csv
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Data paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
REQUESTS_DIR = os.path.join(DATA_DIR, 'requests')
TRANSACTIONS_CSV = os.path.join(DATA_DIR, 'transactions.csv')

# Ensure data directories exist
os.makedirs(REQUESTS_DIR, exist_ok=True)


def load_all_requests():
    """Load all request JSON files from data/requests/"""
    requests_list = []
    
    if not os.path.exists(REQUESTS_DIR):
        logger.warning(f"Requests directory not found: {REQUESTS_DIR}")
        return requests_list
    
    for filename in os.listdir(REQUESTS_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(REQUESTS_DIR, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    requests_list.append(data)
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
    
    # Sort by created_at descending
    requests_list.sort(
        key=lambda x: x.get('metadata', {}).get('created_at', ''),
        reverse=True
    )
    
    return requests_list


def save_to_transactions_csv(request_data):
    """Save approved/rejected request to transactions.csv"""
    try:
        file_exists = os.path.exists(TRANSACTIONS_CSV)
        
        with open(TRANSACTIONS_CSV, 'a', newline='') as csvfile:
            fieldnames = [
                'request_id', 'date', 'member', 'type', 'amount', 
                'budget_line', 'status', 'processed_at', 'treasurer'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            row = {
                'request_id': request_data['metadata']['request_id'],
                'date': request_data['request'].get('date', ''),
                'member': request_data['member']['name'],
                'type': request_data['request']['type'],
                'amount': request_data['request'].get('amount', 0),
                'budget_line': request_data['request'].get('budget_line', ''),
                'status': request_data['metadata']['status'],
                'processed_at': datetime.now().isoformat(),
                'treasurer': request_data['metadata'].get('treasurer', 'Unknown')
            }
            
            writer.writerow(row)
            logger.info(f"Saved to transactions.csv: {row['request_id']}")
            
    except Exception as e:
        logger.error(f"Error saving to CSV: {e}")


@app.route('/api/requests', methods=['GET'])
def get_requests():
    """Get all requests"""
    try:
        requests_list = load_all_requests()
        logger.info(f"Loaded {len(requests_list)} requests")
        return jsonify(requests_list)
    except Exception as e:
        logger.error(f"Error getting requests: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/request/<request_id>', methods=['GET'])
def get_request(request_id):
    """Get a specific request"""
    try:
        requests_list = load_all_requests()
        req = next((r for r in requests_list if r['metadata']['request_id'] == request_id), None)
        
        if not req:
            return jsonify({'error': 'Request not found'}), 404
        
        return jsonify(req)
    except Exception as e:
        logger.error(f"Error getting request {request_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/request/<request_id>/approve', methods=['POST'])
def approve_request(request_id):
    """Approve a request"""
    try:
        data = request.get_json() or {}
        
        # Load the request
        filepath = os.path.join(REQUESTS_DIR, f"{request_id}.json")
        if not os.path.exists(filepath):
            return jsonify({'error': 'Request not found'}), 404
        
        with open(filepath, 'r') as f:
            request_data = json.load(f)
        
        # Update status
        request_data['metadata']['status'] = 'approved'
        request_data['metadata']['updated_at'] = datetime.now().isoformat()
        request_data['metadata']['treasurer'] = data.get('treasurer', 'Unknown')
        request_data['metadata']['notes'] = data.get('notes', '')
        
        # Save updated request
        with open(filepath, 'w') as f:
            json.dump(request_data, f, indent=2)
        
        # Save to transactions CSV
        save_to_transactions_csv(request_data)
        
        logger.info(f"Approved request: {request_id}")
        return jsonify({'success': True, 'request': request_data})
        
    except Exception as e:
        logger.error(f"Error approving request {request_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/request/<request_id>/hold', methods=['POST'])
def hold_request(request_id):
    """Put request on hold"""
    try:
        data = request.get_json() or {}
        
        # Load the request
        filepath = os.path.join(REQUESTS_DIR, f"{request_id}.json")
        if not os.path.exists(filepath):
            return jsonify({'error': 'Request not found'}), 404
        
        with open(filepath, 'r') as f:
            request_data = json.load(f)
        
        # Update status
        request_data['metadata']['status'] = 'on_hold'
        request_data['metadata']['updated_at'] = datetime.now().isoformat()
        request_data['metadata']['treasurer'] = data.get('treasurer', 'Unknown')
        request_data['metadata']['notes'] = data.get('notes', '')
        
        # Save updated request
        with open(filepath, 'w') as f:
            json.dump(request_data, f, indent=2)
        
        logger.info(f"Put on hold: {request_id}")
        return jsonify({'success': True, 'request': request_data})
        
    except Exception as e:
        logger.error(f"Error holding request {request_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/request/<request_id>/reject', methods=['POST'])
def reject_request(request_id):
    """Reject a request"""
    try:
        data = request.get_json() or {}
        
        # Load the request
        filepath = os.path.join(REQUESTS_DIR, f"{request_id}.json")
        if not os.path.exists(filepath):
            return jsonify({'error': 'Request not found'}), 404
        
        with open(filepath, 'r') as f:
            request_data = json.load(f)
        
        # Update status
        request_data['metadata']['status'] = 'rejected'
        request_data['metadata']['updated_at'] = datetime.now().isoformat()
        request_data['metadata']['treasurer'] = data.get('treasurer', 'Unknown')
        request_data['metadata']['notes'] = data.get('notes', '')
        
        # Save updated request
        with open(filepath, 'w') as f:
            json.dump(request_data, f, indent=2)
        
        # Save to transactions CSV
        save_to_transactions_csv(request_data)
        
        logger.info(f"Rejected request: {request_id}")
        return jsonify({'success': True, 'request': request_data})
        
    except Exception as e:
        logger.error(f"Error rejecting request {request_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    static_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(static_dir, path)


@app.route('/')
def index():
    """Redirect to dashboard"""
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'dashboard.html')


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("LBS Treasurer Dashboard API Server")
    logger.info("=" * 60)
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info(f"Requests directory: {REQUESTS_DIR}")
    logger.info(f"Transactions CSV: {TRANSACTIONS_CSV}")
    logger.info("=" * 60)
    
    app.run(host='127.0.0.1', port=8000, debug=True)
