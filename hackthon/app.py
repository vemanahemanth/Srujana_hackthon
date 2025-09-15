# ACTMS - Anti-Corruption Tender Management System
# Main Flask application

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import hashlib
import json

from services.database_service import DatabaseService
from services.ml_service import MLService
from services.chatbot_service import ChatbotService
from services.nlp_service import NLPService
from services.file_handler import FileHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-key-only')
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024  # 15MB max file size
CORS(app, origins=["*"])

# Initialize services
db_service = DatabaseService()
ml_service = MLService()
chatbot_service = ChatbotService()
nlp_service = NLPService()
file_handler = FileHandler()

# API Routes

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """Get dashboard statistics and metrics"""
    try:
        stats = {
            'total_tenders': db_service.count_tenders(),
            'active_bids': db_service.count_active_bids(),
            'suspicious_flags': db_service.count_suspicious_bids(),
            'alerts_today': db_service.count_alerts_today(),
            'tender_status_distribution': db_service.get_tender_status_distribution(),
            'suspicious_score_distribution': db_service.get_suspicion_score_distribution(),
            'recent_suspicious_bids': db_service.get_recent_suspicious_bids(),
            'tender_value_distribution': db_service.get_tender_value_distribution(),
            'activity_timeline': db_service.get_activity_timeline()
        }
        db_service.log_audit('dashboard_accessed', 'system', 'Dashboard data retrieved')
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500

@app.route('/api/tenders', methods=['GET', 'POST'])
def handle_tenders():
    """Handle tender operations"""
    try:
        if request.method == 'GET':
            tenders = db_service.get_all_tenders()
            return jsonify(tenders)
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['title', 'department', 'region', 'deadline', 'budget']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Create tender
            tender_id = db_service.create_tender(
                title=data['title'],
                department=data['department'],
                region=data['region'],
                deadline=data['deadline'],
                budget=float(data['budget']),
                description=data.get('description', ''),
                requirements=data.get('requirements', '')
            )
            
            db_service.log_audit('tender_created', 'system', f'Tender {tender_id} created')
            return jsonify({'tender_id': tender_id, 'message': 'Tender created successfully'})
        
        else:
            return jsonify({'error': 'Method not supported'}), 405
            
    except Exception as e:
        logger.error(f"Tender handling error: {str(e)}")
        return jsonify({'error': 'Failed to process tender request'}), 500

@app.route('/api/bids', methods=['GET', 'POST'])
def handle_bids():
    """Handle bid operations"""
    try:
        if request.method == 'GET':
            tender_id = request.args.get('tender_id')
            if tender_id:
                bids = db_service.get_bids_for_tender(int(tender_id))
            else:
                bids = db_service.get_all_bids()
            return jsonify(bids)
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['tender_id', 'company_name', 'bid_amount', 'proposal_text']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Validate mobile number if provided
            company_info = data.get('company_info', {})
            if 'mobile' in company_info and company_info['mobile']:
                import re
                mobile = re.sub(r'\D', '', str(company_info['mobile']))
                if not (len(mobile) == 12 and mobile.startswith('91') and mobile[2:3] in '6789'):
                    return jsonify({'error': 'Invalid mobile number format. Use Indian mobile number.'}), 400
            
            # Analyze proposal with NLP
            nlp_analysis = nlp_service.analyze_proposal(data['proposal_text'])
            
            # Create bid
            bid_id = db_service.create_bid(
                tender_id=int(data['tender_id']),
                company_name=data['company_name'],
                bid_amount=float(data['bid_amount']),
                proposal_text=data['proposal_text'],
                company_info=data.get('company_info', {}),
                contact_email=data.get('contact_email', ''),
                nlp_score=nlp_analysis.get('quality_score', 0.5)
            )
            
            # Run anomaly detection
            anomaly_result = ml_service.analyze_bid_anomaly(bid_id)
            
            # Update bid with anomaly score
            db_service.update_bid_anomaly_score(
                bid_id, 
                anomaly_result['anomaly_score'], 
                anomaly_result['is_suspicious']
            )
            
            if anomaly_result['is_suspicious']:
                db_service.log_audit('suspicious_bid_detected', 'ml_system', 
                                   f'Suspicious bid {bid_id} detected with score {anomaly_result["anomaly_score"]:.3f}')
            
            db_service.log_audit('bid_submitted', 'system', f'Bid {bid_id} submitted')
            
            return jsonify({
                'bid_id': bid_id, 
                'message': 'Bid submitted successfully',
                'anomaly_analysis': anomaly_result,
                'nlp_analysis': nlp_analysis
            })
        
        else:
            return jsonify({'error': 'Method not supported'}), 405
            
    except Exception as e:
        logger.error(f"Bid handling error: {str(e)}")
        return jsonify({'error': 'Failed to process bid request'}), 500

@app.route('/api/bids/suspicious', methods=['GET'])
def get_suspicious_bids():
    """Get all suspicious bids"""
    try:
        suspicious_bids = db_service.get_suspicious_bids()
        return jsonify(suspicious_bids)
    except Exception as e:
        logger.error(f"Suspicious bids error: {str(e)}")
        return jsonify({'error': 'Failed to fetch suspicious bids'}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get system alerts"""
    try:
        alerts = db_service.get_recent_alerts()
        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Alerts error: {str(e)}")
        return jsonify({'error': 'Failed to fetch alerts'}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chatbot interactions"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get chatbot response
        response = chatbot_service.get_response(message)
        
        db_service.log_audit('chat_interaction', 'user', f'User message: {message[:50]}...')
        
        return jsonify({
            'message': response['message'],
            'source': response['source'],
            'confidence': response.get('confidence', 1.0)
        })
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': 'Failed to process chat message'}), 500

@app.route('/api/model/train', methods=['POST'])
def train_model():
    """Trigger ML model training"""
    try:
        result = ml_service.train_model()
        db_service.log_audit('model_training', 'system', 'ML model training initiated')
        return jsonify(result)
    except Exception as e:
        logger.error(f"Model training error: {str(e)}")
        return jsonify({'error': 'Failed to train model'}), 500

@app.route('/api/model/metrics', methods=['GET'])
def get_model_metrics():
    """Get ML model performance metrics"""
    try:
        metrics = ml_service.get_model_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Model metrics error: {str(e)}")
        return jsonify({'error': 'Failed to fetch model metrics'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle secure file uploads"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Process file upload
        result = file_handler.process_upload(file)
        
        if result['success']:
            db_service.log_audit('file_uploaded', 'user', f'File uploaded: {result["filename"]}')
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        return jsonify({'error': 'Failed to upload file'}), 500

@app.route('/api/audit', methods=['GET'])
def get_audit_logs():
    """Get audit log entries"""
    try:
        limit = request.args.get('limit', 100)
        logs = db_service.get_audit_logs(limit=int(limit))
        return jsonify(logs)
    except Exception as e:
        logger.error(f"Audit logs error: {str(e)}")
        return jsonify({'error': 'Failed to fetch audit logs'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory('uploads', filename)

# Template Routes
@app.route('/')
def index():
    """Serve the home page"""
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    """Serve the dashboard page"""
    return render_template('dashboard.html')

@app.route('/tenders')
def tenders():
    """Serve the tender management page"""
    return render_template('tenders.html')

@app.route('/bids')
def bids():
    """Serve the bid submission page"""
    return render_template('bids.html')

@app.route('/ai-analysis')
def ai_analysis():
    """Serve the AI analysis page"""
    return render_template('ai_analysis.html')

@app.route('/chat')
def chat_page():
    """Serve the full chat page"""
    return render_template('chat.html')

# Additional utility routes
@app.route('/privacy')
def privacy():
    """Privacy policy page"""
    return render_template('legal.html', page_type='privacy')

@app.route('/terms')
def terms():
    """Terms of service page"""
    return render_template('legal.html', page_type='terms')

@app.route('/contact')
def contact():
    """Contact page"""
    return render_template('legal.html', page_type='contact')

@app.route('/docs')
def docs():
    """Documentation page"""
    return render_template('legal.html', page_type='docs')

if __name__ == '__main__':
    # Initialize database on startup
    db_service.initialize_db()
    
    # Initialize ML service
    ml_service.initialize()
    
    logger.info("ACTMS Backend Server Starting...")
    logger.info("Access the application at: http://0.0.0.0:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)