# Chatbot Service - Gemini AI integration with FAQ fallback for ACTMS

import os
import logging
from typing import Dict, List, Any, Optional
import json

# Import Gemini integration
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)

class ChatbotService:
    def __init__(self):
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        self.client = None
        if GEMINI_AVAILABLE and genai and self.gemini_api_key:
            try:
                self.client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {str(e)}")
        elif not GEMINI_AVAILABLE:
            logger.info("Gemini API not available, using FAQ fallback only")
        
        # FAQ database for fallback when Gemini is not available
        self.faq_database = {
            'what is actms': {
                'answer': 'ACTMS (Anti-Corruption Tender Management System) is a comprehensive platform for managing government tenders with AI-powered fraud detection.',
                'confidence': 1.0
            },
            'how to submit bid': {
                'answer': 'To submit a bid: 1) Select a tender, 2) Enter company information, 3) Provide bid amount and proposal, 4) Upload required documents, 5) Submit for review.',
                'confidence': 1.0
            },
            'what is suspicious bid': {
                'answer': 'A suspicious bid is one flagged by our AI system for unusual patterns like extremely low amounts, poor proposal quality, or suspicious timing.',
                'confidence': 1.0
            },
            'how does ai detection work': {
                'answer': 'Our AI uses Isolation Forest algorithm to analyze bid patterns, amounts, proposal quality, and timing to detect potentially fraudulent submissions.',
                'confidence': 1.0
            },
            'what file formats supported': {
                'answer': 'We support common document formats including PDF, DOC, DOCX, TXT, and XLS files up to 15MB in size.',
                'confidence': 1.0
            },
            'how to view tender status': {
                'answer': 'You can view tender status through the dashboard or by accessing the tenders API endpoint which shows active, closed, and upcoming tenders.',
                'confidence': 1.0
            },
            'what is audit log': {
                'answer': 'Audit logs track all system activities including user actions, bid submissions, and security events for compliance and monitoring.',
                'confidence': 1.0
            },
            'how to check system status': {
                'answer': 'System status can be viewed through the dashboard which shows real-time metrics, alerts, and system health indicators.',
                'confidence': 1.0
            }
        }
    
    def get_response(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Get chatbot response using Gemini AI or FAQ fallback"""
        try:
            # Clean and normalize message
            clean_message = message.lower().strip()
            
            # Try Gemini first if available
            if self.client and self.gemini_api_key:
                try:
                    gemini_response = self._get_gemini_response(message, context)
                    if gemini_response:
                        return gemini_response
                except Exception as e:
                    logger.warning(f"Gemini API error, falling back to FAQ: {str(e)}")
            
            # Fallback to FAQ database
            faq_response = self._get_faq_response(clean_message)
            if faq_response:
                return faq_response
            
            # Default response
            return {
                'message': 'I apologize, but I don\'t have a specific answer to your question. Please contact system administrators or check the documentation for more detailed assistance.',
                'source': 'default',
                'confidence': 0.3
            }
            
        except Exception as e:
            logger.error(f"Chatbot service error: {str(e)}")
            return {
                'message': 'I\'m experiencing technical difficulties. Please try again later or contact support.',
                'source': 'error',
                'confidence': 0.0
            }
    
    def _get_gemini_response(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Get response from Gemini AI"""
        try:
            # System prompt for ACTMS context
            system_prompt = """
            You are an AI assistant for ACTMS (Anti-Corruption Tender Management System), 
            a government tender management platform with AI-powered fraud detection.
            
            Key capabilities:
            - Tender management and bid submission
            - AI-powered anomaly detection using Isolation Forest
            - Comprehensive audit logging
            - Secure file handling
            - Real-time alerts for suspicious activities
            
            Provide helpful, accurate information about the system. Be professional and concise.
            If you don't know something specific about the system, acknowledge it and suggest 
            contacting administrators.
            """
            
            # Prepare full prompt with context
            full_prompt = f"{system_prompt}\n\nUser question: {message}"
            
            # Add context if provided
            if context is not None:
                context_str = f"\nAdditional context: {json.dumps(context, indent=2)}"
                full_prompt += context_str
            
            # Get response from Gemini
            if self.client is None:
                raise ValueError("Gemini client not initialized")
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt
            )
            
            content = response.text
            if content is None or content.strip() == "":
                content = "I apologize, but I couldn't generate a response. Please try again."
            
            return {
                'message': content.strip(),
                'source': 'gemini',
                'confidence': 0.9
            }
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return {
                'message': 'I apologize, but I\'m currently unable to provide a response. Please try asking a different question or contact support.',
                'source': 'error',
                'confidence': 0.0
            }
    
    def _get_faq_response(self, message: str) -> Dict[str, Any]:
        """Get response from FAQ database using keyword matching"""
        try:
            # Simple keyword matching
            best_match = None
            best_score = 0
            
            for faq_key, faq_data in self.faq_database.items():
                # Calculate simple keyword overlap score
                faq_keywords = faq_key.split()
                message_words = message.split()
                
                overlap = len(set(faq_keywords) & set(message_words))
                score = overlap / max(len(faq_keywords), 1)
                
                if score > best_score and score > 0.3:  # Minimum threshold
                    best_score = score
                    best_match = faq_data
            
            if best_match:
                return {
                    'message': best_match['answer'],
                    'source': 'faq',
                    'confidence': best_match['confidence'] * best_score
                }
            
            return {
                'message': 'I couldn\'t find an answer to your question in our knowledge base. Please try rephrasing your question or contact support for assistance.',
                'source': 'no_match',
                'confidence': 0.0
            }
            
        except Exception as e:
            logger.error(f"FAQ response error: {str(e)}")
            return {
                'message': 'I encountered an error while searching for an answer. Please try again or contact support.',
                'source': 'error',
                'confidence': 0.0
            }
    
    def add_faq_entry(self, question: str, answer: str, confidence: float = 1.0):
        """Add new FAQ entry"""
        try:
            key = question.lower().strip()
            self.faq_database[key] = {
                'answer': answer,
                'confidence': confidence
            }
            logger.info(f"FAQ entry added: {key}")
        except Exception as e:
            logger.error(f"FAQ entry addition error: {str(e)}")
    
    def get_conversation_context(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get conversation context for personalized responses"""
        # This could be extended to store and retrieve conversation history
        # For now, return basic system status
        try:
            from services.database_service import DatabaseService
            db_service = DatabaseService()
            
            context = {
                'total_tenders': db_service.count_tenders(),
                'active_bids': db_service.count_active_bids(),
                'suspicious_flags': db_service.count_suspicious_bids(),
                'recent_alerts': len(db_service.get_recent_alerts(limit=5))
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Context retrieval error: {str(e)}")
            return {}
    
    def is_gemini_available(self) -> bool:
        """Check if Gemini integration is available"""
        return self.client is not None and self.gemini_api_key is not None