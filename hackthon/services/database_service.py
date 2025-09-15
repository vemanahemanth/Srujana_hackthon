# Database Service - SQLite operations for ACTMS

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_path='actms.db'):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def initialize_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Tenders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tenders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    department TEXT NOT NULL,
                    region TEXT NOT NULL,
                    budget REAL NOT NULL,
                    deadline TEXT NOT NULL,
                    requirements TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Bids table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tender_id INTEGER NOT NULL,
                    company_name TEXT NOT NULL,
                    bid_amount REAL NOT NULL,
                    proposal_text TEXT NOT NULL,
                    company_info TEXT DEFAULT '{}',
                    contact_email TEXT,
                    file_hash TEXT,
                    file_path TEXT,
                    anomaly_score REAL DEFAULT 0.0,
                    is_suspicious INTEGER DEFAULT 0,
                    nlp_score REAL DEFAULT 0.5,
                    status TEXT DEFAULT 'submitted',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tender_id) REFERENCES tenders (id)
                )
            ''')
            
            # Audit logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    severity TEXT DEFAULT 'medium',
                    related_id INTEGER,
                    related_type TEXT,
                    is_read INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def log_audit(self, action: str, user_id: str, details: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log audit event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO audit_logs (action, user_id, details, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (action, user_id, details, ip_address, user_agent))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Audit logging error: {str(e)}")
            conn.rollback()
        finally:
            conn.close()
    
    def create_tender(self, title: str, department: str, region: str, 
                     deadline: str, budget: float, description: str = '', 
                     requirements: str = '') -> int:
        """Create new tender"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO tenders (title, description, department, region, budget, deadline, requirements)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, department, region, budget, deadline, requirements))
            
            tender_id = cursor.lastrowid
            conn.commit()
            
            if tender_id is None:
                raise ValueError("Failed to create tender: no ID returned")
            return tender_id
            
        except Exception as e:
            logger.error(f"Tender creation error: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def create_bid(self, tender_id: int, company_name: str, bid_amount: float,
                   proposal_text: str, company_info: Optional[Dict] = None, contact_email: str = '',
                   file_hash: Optional[str] = None, file_path: Optional[str] = None, nlp_score: float = 0.5) -> int:
        """Create new bid"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            company_info_json = json.dumps(company_info or {})
            
            cursor.execute('''
                INSERT INTO bids (tender_id, company_name, bid_amount, proposal_text, 
                                company_info, contact_email, file_hash, file_path, nlp_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (tender_id, company_name, bid_amount, proposal_text, 
                  company_info_json, contact_email, file_hash, file_path, nlp_score))
            
            bid_id = cursor.lastrowid
            conn.commit()
            
            if bid_id is None:
                raise ValueError("Failed to create bid: no ID returned")
            return bid_id
            
        except Exception as e:
            logger.error(f"Bid creation error: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def update_bid_anomaly_score(self, bid_id: int, anomaly_score: float, is_suspicious: bool):
        """Update bid with anomaly analysis results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE bids SET anomaly_score = ?, is_suspicious = ?
                WHERE id = ?
            ''', (anomaly_score, int(is_suspicious), bid_id))
            
            conn.commit()
            
            # Create alert if suspicious
            if is_suspicious:
                self.create_alert(
                    type='anomaly_detection',
                    title='Suspicious Bid Detected',
                    message=f'Bid #{bid_id} flagged as suspicious with anomaly score {anomaly_score:.3f}',
                    severity='high',
                    related_id=bid_id,
                    related_type='bid'
                )
            
        except Exception as e:
            logger.error(f"Bid anomaly update error: {str(e)}")
            conn.rollback()
        finally:
            conn.close()
    
    def create_alert(self, type: str, title: str, message: str, 
                    severity: str = 'medium', related_id: Optional[int] = None, related_type: Optional[str] = None):
        """Create system alert"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO alerts (type, title, message, severity, related_id, related_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (type, title, message, severity, related_id, related_type))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Alert creation error: {str(e)}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_all_tenders(self) -> List[Dict]:
        """Get all tenders"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM tenders ORDER BY created_at DESC
            ''')
            
            tenders = [dict(row) for row in cursor.fetchall()]
            return tenders
            
        except Exception as e:
            logger.error(f"Tender retrieval error: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_all_bids(self) -> List[Dict]:
        """Get all bids with tender information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT b.*, t.title as tender_title, t.department
                FROM bids b
                JOIN tenders t ON b.tender_id = t.id
                ORDER BY b.created_at DESC
            ''')
            
            bids = []
            for row in cursor.fetchall():
                bid = dict(row)
                if bid['company_info']:
                    bid['company_info'] = json.loads(bid['company_info'])
                bids.append(bid)
            
            return bids
            
        except Exception as e:
            logger.error(f"Bid retrieval error: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_bids_for_tender(self, tender_id: int) -> List[Dict]:
        """Get bids for specific tender"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM bids WHERE tender_id = ? ORDER BY created_at DESC
            ''', (tender_id,))
            
            bids = []
            for row in cursor.fetchall():
                bid = dict(row)
                if bid['company_info']:
                    bid['company_info'] = json.loads(bid['company_info'])
                bids.append(bid)
            
            return bids
            
        except Exception as e:
            logger.error(f"Tender bids retrieval error: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_suspicious_bids(self) -> List[Dict]:
        """Get all suspicious bids"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT b.*, t.title as tender_title, t.department
                FROM bids b
                JOIN tenders t ON b.tender_id = t.id
                WHERE b.is_suspicious = 1
                ORDER BY b.anomaly_score DESC, b.created_at DESC
            ''')
            
            bids = []
            for row in cursor.fetchall():
                bid = dict(row)
                if bid['company_info']:
                    bid['company_info'] = json.loads(bid['company_info'])
                bids.append(bid)
            
            return bids
            
        except Exception as e:
            logger.error(f"Suspicious bids retrieval error: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent system alerts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM alerts 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            alerts = [dict(row) for row in cursor.fetchall()]
            return alerts
            
        except Exception as e:
            logger.error(f"Alerts retrieval error: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_audit_logs(self, limit: int = 100) -> List[Dict]:
        """Get audit log entries"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM audit_logs 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            logs = [dict(row) for row in cursor.fetchall()]
            return logs
            
        except Exception as e:
            logger.error(f"Audit logs retrieval error: {str(e)}")
            return []
        finally:
            conn.close()
    
    def count_tenders(self) -> int:
        """Count total tenders"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) as count FROM tenders')
            result = cursor.fetchone()
            return result['count'] if result else 0
        except:
            return 0
        finally:
            conn.close()
    
    def count_active_bids(self) -> int:
        """Count active bids"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) as count FROM bids WHERE status = 'submitted'")
            result = cursor.fetchone()
            return result['count'] if result else 0
        except:
            return 0
        finally:
            conn.close()
    
    def count_suspicious_bids(self) -> int:
        """Count suspicious bids"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) as count FROM bids WHERE is_suspicious = 1')
            result = cursor.fetchone()
            return result['count'] if result else 0
        except:
            return 0
        finally:
            conn.close()
    
    def count_alerts_today(self) -> int:
        """Count alerts created today"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(*) as count FROM alerts 
                WHERE DATE(created_at) = ?
            ''', (today,))
            result = cursor.fetchone()
            return result['count'] if result else 0
        except:
            return 0
        finally:
            conn.close()
    
    def get_tender_status_distribution(self) -> Dict:
        """Get tender status distribution for dashboard"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM tenders 
                GROUP BY status
            ''')
            
            distribution = {}
            for row in cursor.fetchall():
                distribution[row['status']] = row['count']
            
            return distribution
            
        except Exception as e:
            logger.error(f"Tender status distribution error: {str(e)}")
            return {}
        finally:
            conn.close()
    
    def get_suspicion_score_distribution(self) -> List[Dict]:
        """Get suspicion score distribution"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN anomaly_score < 0.3 THEN 'Low Risk'
                        WHEN anomaly_score < 0.7 THEN 'Medium Risk'
                        ELSE 'High Risk'
                    END as risk_level,
                    COUNT(*) as count
                FROM bids 
                GROUP BY risk_level
            ''')
            
            distribution = []
            for row in cursor.fetchall():
                distribution.append({
                    'risk_level': row['risk_level'],
                    'count': row['count']
                })
            
            return distribution
            
        except Exception as e:
            logger.error(f"Suspicion score distribution error: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_recent_suspicious_bids(self, limit: int = 10) -> List[Dict]:
        """Get recent suspicious bids for dashboard"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT b.id, b.company_name, b.bid_amount, b.anomaly_score, 
                       t.title as tender_title, b.created_at
                FROM bids b
                JOIN tenders t ON b.tender_id = t.id
                WHERE b.is_suspicious = 1
                ORDER BY b.created_at DESC
                LIMIT ?
            ''', (limit,))
            
            bids = [dict(row) for row in cursor.fetchall()]
            return bids
            
        except Exception as e:
            logger.error(f"Recent suspicious bids error: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_tender_value_distribution(self) -> List[Dict]:
        """Get tender value distribution for analytics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN budget < 100000 THEN 'Under $100K'
                        WHEN budget < 500000 THEN '$100K - $500K'
                        WHEN budget < 1000000 THEN '$500K - $1M'
                        ELSE 'Over $1M'
                    END as value_range,
                    COUNT(*) as count
                FROM tenders 
                GROUP BY value_range
            ''')
            
            distribution = []
            for row in cursor.fetchall():
                distribution.append({
                    'value_range': row['value_range'],
                    'count': row['count']
                })
            
            return distribution
            
        except Exception as e:
            logger.error(f"Tender value distribution error: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_activity_timeline(self, days: int = 30) -> List[Dict]:
        """Get activity timeline for dashboard chart"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            cursor.execute('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as tender_count,
                    0 as bid_count
                FROM tenders 
                WHERE DATE(created_at) >= ?
                GROUP BY DATE(created_at)
                
                UNION ALL
                
                SELECT 
                    DATE(created_at) as date,
                    0 as tender_count,
                    COUNT(*) as bid_count
                FROM bids 
                WHERE DATE(created_at) >= ?
                GROUP BY DATE(created_at)
                
                ORDER BY date
            ''', (start_date, start_date))
            
            timeline = []
            for row in cursor.fetchall():
                timeline.append(dict(row))
            
            return timeline
            
        except Exception as e:
            logger.error(f"Activity timeline error: {str(e)}")
            return []
        finally:
            conn.close()