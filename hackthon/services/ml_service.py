# ML Service - Isolation Forest anomaly detection for ACTMS

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import os
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class MLService:
    def __init__(self, model_path='models'):
        self.model_path = model_path
        self.model_file = os.path.join(model_path, 'isolation_forest.pkl')
        self.scaler_file = os.path.join(model_path, 'scaler.pkl')
        self.model = None
        self.scaler = None
        self.contamination = 0.1  # 10% contamination threshold
        self.feature_names = [
            'bid_amount', 'bid_amount_normalized', 'proposal_length',
            'company_name_length', 'submission_hour', 'submission_day_of_week',
            'nlp_score', 'time_to_deadline_hours'
        ]
        
        # Ensure models directory exists
        os.makedirs(model_path, exist_ok=True)
    
    def initialize(self):
        """Initialize ML service and load existing models"""
        try:
            if os.path.exists(self.model_file) and os.path.exists(self.scaler_file):
                self.model = joblib.load(self.model_file)
                self.scaler = joblib.load(self.scaler_file)
                logger.info("Existing ML models loaded successfully")
            else:
                # Create default model for initial use
                self.create_default_model()
                logger.info("Default ML models created")
        except Exception as e:
            logger.error(f"ML service initialization error: {str(e)}")
            self.create_default_model()
    
    def create_default_model(self):
        """Create default model for initial use"""
        try:
            self.model = IsolationForest(
                contamination=float(self.contamination),  # type: ignore
                random_state=42,
                n_estimators=100
            )
            self.scaler = StandardScaler()
            
            # Create synthetic training data for initial model
            synthetic_data = self._generate_synthetic_training_data()
            features = self._extract_features_from_synthetic(synthetic_data)
            
            if len(features) > 0:
                # Fit scaler and model
                features_scaled = self.scaler.fit_transform(features)
                self.model.fit(features_scaled)
                
                # Save models
                self._save_models()
                logger.info("Default models created and saved")
            
        except Exception as e:
            logger.error(f"Default model creation error: {str(e)}")
    
    def _generate_synthetic_training_data(self, n_samples: int = 100) -> List[Dict]:
        """Generate synthetic training data for initial model"""
        import random
        
        synthetic_data = []
        
        for i in range(n_samples):
            # Normal bids (90%)
            if i < n_samples * 0.9:
                bid_data = {
                    'id': i,
                    'tender_id': random.randint(1, 10),
                    'company_name': f'Company_{i}',
                    'bid_amount': random.uniform(10000, 500000),
                    'proposal_text': 'A' * random.randint(100, 1000),
                    'nlp_score': random.uniform(0.4, 0.8),
                    'created_at': '2024-01-01 10:00:00',
                    'tender_budget': random.uniform(50000, 1000000),
                    'tender_deadline': '2024-12-31 23:59:59'
                }
            # Anomalous bids (10%)
            else:
                bid_data = {
                    'id': i,
                    'tender_id': random.randint(1, 10),
                    'company_name': f'SuspiciousCompany_{i}',
                    'bid_amount': random.uniform(1000, 10000),  # Unusually low
                    'proposal_text': 'Short proposal',  # Unusually short
                    'nlp_score': random.uniform(0.1, 0.3),  # Low quality
                    'created_at': '2024-01-01 02:00:00',  # Unusual time
                    'tender_budget': random.uniform(50000, 1000000),
                    'tender_deadline': '2024-12-31 23:59:59'
                }
            
            synthetic_data.append(bid_data)
        
        return synthetic_data
    
    def _extract_features_from_synthetic(self, bid_data: List[Dict]) -> np.ndarray:
        """Extract features from synthetic bid data"""
        features = []
        
        for bid in bid_data:
            try:
                feature_vector = self._extract_single_bid_features(bid, bid.get('tender_budget', 100000))
                if len(feature_vector) == len(self.feature_names):
                    features.append(feature_vector)
            except Exception as e:
                logger.warning(f"Feature extraction error for bid {bid.get('id', 'unknown')}: {str(e)}")
                continue
        
        return np.array(features) if features else np.array([]).reshape(0, len(self.feature_names))
    
    def _extract_single_bid_features(self, bid: Dict, tender_budget: float) -> List[float]:
        """Extract features from a single bid"""
        try:
            bid_amount = float(bid.get('bid_amount', 0))
            proposal_text = bid.get('proposal_text', '')
            company_name = bid.get('company_name', '')
            created_at = bid.get('created_at', '2024-01-01 12:00:00')
            nlp_score = float(bid.get('nlp_score', 0.5))
            
            # Parse timestamp
            from datetime import datetime
            try:
                timestamp = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
            except:
                timestamp = datetime.now()
            
            # Calculate deadline proximity (default to 30 days if not available)
            deadline_str = bid.get('tender_deadline', '2024-12-31 23:59:59')
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M:%S')
                time_to_deadline = (deadline - timestamp).total_seconds() / 3600  # hours
            except:
                time_to_deadline = 24 * 30  # Default to 30 days
            
            features = [
                bid_amount,
                bid_amount / max(tender_budget, 1),  # Normalized bid amount
                len(proposal_text),
                len(company_name),
                timestamp.hour,
                timestamp.weekday(),
                nlp_score,
                max(time_to_deadline, 0)
            ]
            
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction error: {str(e)}")
            return [0.0] * len(self.feature_names)
    
    def analyze_bid_anomaly(self, bid_id: int) -> Dict[str, Any]:
        """Analyze bid for anomalies using trained model"""
        try:
            # Import database service to get bid data
            from services.database_service import DatabaseService
            db_service = DatabaseService()
            
            # Get bid data
            conn = db_service.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT b.*, t.budget as tender_budget, t.deadline as tender_deadline
                FROM bids b
                JOIN tenders t ON b.tender_id = t.id
                WHERE b.id = ?
            ''', (bid_id,))
            
            bid_row = cursor.fetchone()
            conn.close()
            
            if not bid_row:
                return {
                    'bid_id': bid_id,
                    'anomaly_score': 0.5,
                    'is_suspicious': False,
                    'error': 'Bid not found'
                }
            
            bid_data = dict(bid_row)
            
            # Extract features
            features = self._extract_single_bid_features(bid_data, bid_data.get('tender_budget', 100000))
            
            if self.model is None or self.scaler is None:
                self.initialize()
            
            if self.model is None or self.scaler is None:
                return {
                    'bid_id': bid_id,
                    'anomaly_score': 0.5,
                    'is_suspicious': False,
                    'error': 'Model not available'
                }
            
            # Scale features
            features_array = np.array(features).reshape(1, -1)
            features_scaled = self.scaler.transform(features_array)
            
            # Get anomaly score
            anomaly_scores = self.model.decision_function(features_scaled)
            anomaly_score = float(anomaly_scores[0])
            
            # Predict if anomalous (inlier = 1, outlier = -1)
            predictions = self.model.predict(features_scaled)
            is_suspicious = bool(predictions[0] == -1)
            
            # Normalize anomaly score to 0-1 range
            normalized_score = max(0, min(1, (anomaly_score + 1) / 2))
            
            return {
                'bid_id': bid_id,
                'anomaly_score': normalized_score,
                'is_suspicious': is_suspicious,
                'raw_score': anomaly_score,
                'features_analyzed': dict(zip(self.feature_names, features))
            }
            
        except Exception as e:
            logger.error(f"Bid anomaly analysis error: {str(e)}")
            return {
                'bid_id': bid_id,
                'anomaly_score': 0.5,
                'is_suspicious': False,
                'error': str(e)
            }
    
    def train_model(self, retrain: bool = False) -> Dict[str, Any]:
        """Train or retrain the ML model using current bid data"""
        try:
            # Import database service
            from services.database_service import DatabaseService
            db_service = DatabaseService()
            
            # Get all bids with tender information
            conn = db_service.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT b.*, t.budget as tender_budget, t.deadline as tender_deadline
                FROM bids b
                JOIN tenders t ON b.tender_id = t.id
                ORDER BY b.created_at
            ''')
            
            bid_rows = cursor.fetchall()
            conn.close()
            
            if len(bid_rows) < 10:
                # Not enough data, use synthetic data
                synthetic_data = self._generate_synthetic_training_data(100)
                training_features = self._extract_features_from_synthetic(synthetic_data)
                logger.info("Using synthetic training data due to insufficient real data")
            else:
                # Extract features from real bids
                training_features = []
                for row in bid_rows:
                    bid_data = dict(row)
                    features = self._extract_single_bid_features(bid_data, bid_data.get('tender_budget', 100000))
                    if len(features) == len(self.feature_names):
                        training_features.append(features)
                
                training_features = np.array(training_features)
                logger.info(f"Using {len(training_features)} real bids for training")
            
            if len(training_features) == 0:
                return {
                    'success': False,
                    'error': 'No valid training data available',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Initialize or retrain model
            if retrain or self.model is None:
                self.model = IsolationForest(
                    contamination=float(self.contamination),  # type: ignore
                    random_state=42,
                    n_estimators=100
                )
                self.scaler = StandardScaler()
            
            # Fit scaler and model
            if self.scaler is None:
                raise ValueError("Scaler is not initialized")
            if self.model is None:
                raise ValueError("Model is not initialized")
            
            features_scaled = self.scaler.fit_transform(training_features)
            self.model.fit(features_scaled)
            
            # Save models
            self._save_models()
            
            # Calculate training metrics
            predictions = self.model.predict(features_scaled)
            anomaly_scores = self.model.decision_function(features_scaled)
            
            n_outliers = np.sum(predictions == -1)
            outlier_percentage = (n_outliers / len(predictions)) * 100
            
            training_result = {
                'success': True,
                'n_samples': len(training_features),
                'n_outliers_detected': int(n_outliers),
                'outlier_percentage': round(outlier_percentage, 2),
                'contamination_threshold': self.contamination,
                'feature_names': self.feature_names,
                'model_saved': True,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Model training completed: {training_result}")
            return training_result
            
        except Exception as e:
            logger.error(f"Model training error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            if self.model is not None:
                joblib.dump(self.model, self.model_file)
            if self.scaler is not None:
                joblib.dump(self.scaler, self.scaler_file)
            logger.info("Models saved successfully")
        except Exception as e:
            logger.error(f"Model saving error: {str(e)}")
    
    def get_model_metrics(self) -> Dict[str, Any]:
        """Get ML model performance metrics and status"""
        try:
            model_status = {
                'model_loaded': self.model is not None,
                'scaler_loaded': self.scaler is not None,
                'contamination_threshold': self.contamination,
                'feature_count': len(self.feature_names),
                'feature_names': self.feature_names
            }
            
            # Add file information if models exist
            if os.path.exists(self.model_file):
                model_stat = os.stat(self.model_file)
                model_status['model_file_size'] = model_stat.st_size
                model_status['model_last_modified'] = datetime.fromtimestamp(model_stat.st_mtime).isoformat()
            
            if os.path.exists(self.scaler_file):
                scaler_stat = os.stat(self.scaler_file)
                model_status['scaler_file_size'] = scaler_stat.st_size
                model_status['scaler_last_modified'] = datetime.fromtimestamp(scaler_stat.st_mtime).isoformat()
            
            # Add model parameters if available
            if self.model is not None:
                if hasattr(self.model, 'n_estimators'):
                    model_status['n_estimators'] = self.model.n_estimators
                if hasattr(self.model, 'max_samples'):
                    model_status['max_samples'] = self.model.max_samples
            
            return model_status
            
        except Exception as e:
            logger.error(f"Model metrics error: {str(e)}")
            return {
                'error': str(e),
                'model_loaded': False,
                'scaler_loaded': False
            }
    
    def analyze_feature_importance(self) -> Dict[str, Any]:
        """Analyze feature importance and patterns"""
        try:
            # Import database service
            from services.database_service import DatabaseService
            db_service = DatabaseService()
            
            # Get suspicious vs normal bids
            suspicious_bids = db_service.get_suspicious_bids()
            all_bids = db_service.get_all_bids()
            normal_bids = [bid for bid in all_bids if not bid.get('is_suspicious', False)]
            
            if len(suspicious_bids) == 0 or len(normal_bids) == 0:
                return {
                    'error': 'Insufficient data for feature analysis',
                    'suspicious_count': len(suspicious_bids),
                    'normal_count': len(normal_bids)
                }
            
            # Extract features for both groups
            suspicious_features = []
            normal_features = []
            
            for bid in suspicious_bids:
                features = self._extract_single_bid_features(bid, bid.get('tender_budget', 100000))
                suspicious_features.append(features)
            
            for bid in normal_bids[:len(suspicious_bids) * 2]:  # Limit normal bids for comparison
                features = self._extract_single_bid_features(bid, bid.get('tender_budget', 100000))
                normal_features.append(features)
            
            suspicious_features = np.array(suspicious_features)
            normal_features = np.array(normal_features)
            
            # Calculate feature statistics
            feature_analysis = {}
            for i, feature_name in enumerate(self.feature_names):
                suspicious_values = suspicious_features[:, i] if len(suspicious_features) > 0 else np.array([])
                normal_values = normal_features[:, i] if len(normal_features) > 0 else np.array([])
                
                feature_analysis[feature_name] = {
                    'suspicious_mean': float(np.mean(suspicious_values)) if len(suspicious_values) > 0 else 0,
                    'normal_mean': float(np.mean(normal_values)) if len(normal_values) > 0 else 0,
                    'suspicious_std': float(np.std(suspicious_values)) if len(suspicious_values) > 0 else 0,
                    'normal_std': float(np.std(normal_values)) if len(normal_values) > 0 else 0
                }
                
                # Calculate difference ratio
                if feature_analysis[feature_name]['normal_mean'] != 0:
                    ratio = feature_analysis[feature_name]['suspicious_mean'] / feature_analysis[feature_name]['normal_mean']
                    feature_analysis[feature_name]['difference_ratio'] = float(ratio)
                else:
                    feature_analysis[feature_name]['difference_ratio'] = 1.0
            
            return {
                'feature_analysis': feature_analysis,
                'suspicious_count': len(suspicious_bids),
                'normal_count': len(normal_bids),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Feature importance analysis error: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }