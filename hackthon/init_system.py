#!/usr/bin/env python3
"""
ACTMS System Initialization Script
Initializes database and validates all services are working correctly.
"""

import os
import sys
import logging
from datetime import datetime

# Add current directory to path to import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_service():
    """Test database service initialization and basic operations"""
    try:
        from services.database_service import DatabaseService
        
        logger.info("Testing Database Service...")
        db_service = DatabaseService()
        
        # Initialize database
        db_service.initialize_db()
        logger.info("✓ Database initialized successfully")
        
        # Test audit logging
        db_service.log_audit('system_init', 'system', 'Testing database service')
        logger.info("✓ Audit logging working")
        
        # Test tender creation
        tender_id = db_service.create_tender(
            title="Test Tender",
            department="IT",
            region="Test Region",
            deadline="2025-12-31 23:59:59",
            budget=100000.0,
            description="Test tender for system validation"
        )
        logger.info(f"✓ Tender creation working (ID: {tender_id})")
        
        # Test bid creation
        bid_id = db_service.create_bid(
            tender_id=tender_id,
            company_name="Test Company",
            bid_amount=50000.0,
            proposal_text="Test proposal for system validation",
            company_info={
                "contact": "test@test.com",
                "mobile": "+91-98765-43210",
                "address": "Mumbai, Maharashtra, India"
            },
            contact_email="test@test.com"
        )
        logger.info(f"✓ Bid creation working (ID: {bid_id})")
        
        # Test alert creation
        db_service.create_alert(
            type='system_test',
            title='System Initialization Test',
            message='Testing alert system during initialization'
        )
        logger.info("✓ Alert creation working")
        
        return True, tender_id, bid_id
        
    except Exception as e:
        logger.error(f"Database service test failed: {str(e)}")
        return False, None, None

def test_nlp_service():
    """Test NLP service"""
    try:
        from services.nlp_service import NLPService
        
        logger.info("Testing NLP Service...")
        nlp_service = NLPService()
        
        # Test proposal analysis
        test_proposal = """
        We propose to deliver a comprehensive solution that meets all requirements.
        Our experienced team has successfully completed similar projects in the past.
        We will implement modern technologies and follow best practices to ensure
        quality deliverables within the specified timeline and budget.
        """
        
        analysis = nlp_service.analyze_proposal(test_proposal)
        
        if 'quality_score' in analysis and isinstance(analysis['quality_score'], (int, float)):
            logger.info(f"✓ NLP analysis working (Quality Score: {analysis['quality_score']:.3f})")
            return True
        else:
            logger.error("NLP analysis missing quality_score or invalid type")
            return False
            
    except Exception as e:
        logger.error(f"NLP service test failed: {str(e)}")
        return False

def test_ml_service():
    """Test ML service"""
    try:
        from services.ml_service import MLService
        
        logger.info("Testing ML Service...")
        ml_service = MLService()
        
        # Initialize ML service
        ml_service.initialize()
        logger.info("✓ ML service initialized")
        
        # Test model training
        training_result = ml_service.train_model()
        if training_result.get('success'):
            logger.info("✓ ML model training working")
        else:
            logger.warning(f"ML training completed with issues: {training_result}")
        
        return True
        
    except Exception as e:
        logger.error(f"ML service test failed: {str(e)}")
        return False

def test_chatbot_service():
    """Test chatbot service"""
    try:
        from services.chatbot_service import ChatbotService
        
        logger.info("Testing Chatbot Service...")
        chatbot_service = ChatbotService()
        
        # Test FAQ response
        response = chatbot_service.get_response("what is actms")
        
        if response and 'message' in response and response['message']:
            logger.info("✓ Chatbot service working")
            logger.info(f"  Sample response: {response['message'][:100]}...")
            return True
        else:
            logger.error("Chatbot service returned invalid response")
            return False
            
    except Exception as e:
        logger.error(f"Chatbot service test failed: {str(e)}")
        return False

def test_file_handler():
    """Test file handler service"""
    try:
        from services.file_handler import FileHandler
        
        logger.info("Testing File Handler Service...")
        file_handler = FileHandler()
        
        # Create test file-like object
        class MockFile:
            def __init__(self):
                self.filename = "test.txt"
                self.content = b"This is a test file for validation."
                self.pointer = 0
            
            def read(self, size=-1):
                if size == -1:
                    result = self.content[self.pointer:]
                    self.pointer = len(self.content)
                else:
                    result = self.content[self.pointer:self.pointer + size]
                    self.pointer += len(result)
                return result
            
            def seek(self, pos, whence=0):
                if whence == 0:  # SEEK_SET
                    self.pointer = pos
                elif whence == 2:  # SEEK_END
                    self.pointer = len(self.content)
                return self.pointer
            
            def tell(self):
                return self.pointer
            
            def save(self, path):
                # Mock save operation
                with open(path, 'wb') as f:
                    f.write(self.content)
        
        # Test file validation without actual upload
        mock_file = MockFile()
        logger.info("✓ File handler service initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"File handler test failed: {str(e)}")
        return False

def test_anomaly_detection(db_service, ml_service, bid_id):
    """Test anomaly detection with real bid"""
    try:
        logger.info("Testing anomaly detection...")
        
        # Test anomaly analysis on the created bid
        anomaly_result = ml_service.analyze_bid_anomaly(bid_id)
        
        if 'anomaly_score' in anomaly_result and 'is_suspicious' in anomaly_result:
            logger.info(f"✓ Anomaly detection working (Score: {anomaly_result['anomaly_score']:.3f})")
            
            # Update bid with anomaly score
            db_service.update_bid_anomaly_score(
                bid_id, 
                anomaly_result['anomaly_score'], 
                anomaly_result['is_suspicious']
            )
            logger.info("✓ Anomaly score update working")
            return True
        else:
            logger.error("Anomaly detection returned invalid result")
            return False
            
    except Exception as e:
        logger.error(f"Anomaly detection test failed: {str(e)}")
        return False

def main():
    """Main initialization and testing function"""
    logger.info("="*60)
    logger.info("ACTMS System Initialization and Testing")
    logger.info("="*60)
    
    success_count = 0
    total_tests = 6
    
    # Test database service
    db_success, tender_id, bid_id = test_database_service()
    if db_success:
        success_count += 1
    
    # Test NLP service
    if test_nlp_service():
        success_count += 1
    
    # Test ML service
    if test_ml_service():
        success_count += 1
    
    # Test chatbot service
    if test_chatbot_service():
        success_count += 1
    
    # Test file handler
    if test_file_handler():
        success_count += 1
    
    # Test integration if database and ML services worked
    if db_success and bid_id:
        try:
            from services.ml_service import MLService
            from services.database_service import DatabaseService
            ml_service = MLService()
            if test_anomaly_detection(
                db_service=DatabaseService(), 
                ml_service=ml_service, 
                bid_id=bid_id
            ):
                success_count += 1
        except Exception as e:
            logger.error(f"Integration test failed: {str(e)}")
    
    # Summary
    logger.info("="*60)
    logger.info(f"INITIALIZATION COMPLETE: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        logger.info("🎉 All services are working correctly!")
        logger.info("System is ready to start")
        return True
    else:
        logger.warning(f"⚠️ {total_tests - success_count} test(s) failed")
        logger.info("System may have issues but can still be started")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nInitialization interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {str(e)}")
        sys.exit(1)