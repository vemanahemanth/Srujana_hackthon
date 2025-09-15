# NLP Service - Natural Language Processing for proposal analysis in ACTMS

import spacy
import logging
from typing import Dict, Any, Optional
import re
import os

logger = logging.getLogger(__name__)

class NLPService:
    def __init__(self):
        self.nlp = None
        self.model_name = "en_core_web_sm"
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize spaCy model with fallback"""
        try:
            # Try to load the English model
            self.nlp = spacy.load(self.model_name)
            logger.info(f"SpaCy model '{self.model_name}' loaded successfully")
        except OSError:
            try:
                # Try to download the model using subprocess
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", self.model_name], check=True)
                self.nlp = spacy.load(self.model_name)
                logger.info(f"SpaCy model '{self.model_name}' downloaded and loaded")
            except Exception as e:
                logger.warning(f"Could not load spaCy model: {str(e)}. Using fallback analysis.")
                self.nlp = None
    
    def analyze_proposal(self, text: str) -> Dict[str, Any]:
        """
        Analyze proposal text and return quality metrics
        
        Args:
            text: The proposal text to analyze
            
        Returns:
            Dictionary containing analysis results including quality_score
        """
        if not text or not isinstance(text, str):
            return {
                'quality_score': 0.0,
                'word_count': 0,
                'sentence_count': 0,
                'readability_score': 0.0,
                'technical_terms_count': 0,
                'completeness_score': 0.0,
                'professional_score': 0.0,
                'error': 'Invalid or empty text'
            }
        
        try:
            # Basic text metrics
            word_count = len(text.split())
            sentence_count = len(re.split(r'[.!?]+', text.strip()))
            
            # Initialize scores
            quality_metrics = {
                'word_count': word_count,
                'sentence_count': sentence_count,
                'readability_score': self._calculate_readability(text),
                'technical_terms_count': self._count_technical_terms(text),
                'completeness_score': self._assess_completeness(text),
                'professional_score': self._assess_professionalism(text)
            }
            
            # Advanced analysis with spaCy if available
            if self.nlp is not None:
                advanced_metrics = self._analyze_with_spacy(text)
                if advanced_metrics:  # Only update if we got valid metrics
                    quality_metrics.update(advanced_metrics)
            
            # Calculate overall quality score
            quality_score = self._calculate_quality_score(quality_metrics)
            quality_metrics['quality_score'] = quality_score
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Proposal analysis error: {str(e)}")
            return {
                'quality_score': 0.5,  # Default middle score
                'word_count': len(text.split()) if text else 0,
                'sentence_count': 1,
                'readability_score': 0.5,
                'technical_terms_count': 0,
                'completeness_score': 0.5,
                'professional_score': 0.5,
                'error': str(e)
            }
    
    def _calculate_readability(self, text: str) -> float:
        """Calculate basic readability score using Flesch formula approximation"""
        try:
            words = text.split()
            sentences = re.split(r'[.!?]+', text.strip())
            syllables = sum(self._count_syllables(word) for word in words)
            
            if len(sentences) == 0 or len(words) == 0:
                return 0.0
            
            # Simplified Flesch Reading Ease approximation
            avg_sentence_length = len(words) / len(sentences)
            avg_syllables_per_word = syllables / len(words)
            
            score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
            
            # Normalize to 0-1 scale
            return max(0.0, min(1.0, score / 100.0))
            
        except Exception:
            return 0.5
    
    def _count_syllables(self, word: str) -> int:
        """Simple syllable counting heuristic"""
        word = word.lower().strip()
        if not word:
            return 0
        
        vowels = "aeiouy"
        syllable_count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel
        
        # Handle silent 'e'
        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1
        
        return max(1, syllable_count)
    
    def _count_technical_terms(self, text: str) -> int:
        """Count technical/business terms that indicate expertise"""
        technical_terms = [
            'specification', 'requirements', 'implementation', 'methodology',
            'deliverable', 'milestone', 'compliance', 'quality assurance',
            'project management', 'risk assessment', 'stakeholder', 'framework',
            'infrastructure', 'procurement', 'contract', 'budget', 'timeline',
            'resource', 'capability', 'expertise', 'experience', 'qualification'
        ]
        
        text_lower = text.lower()
        count = sum(1 for term in technical_terms if term in text_lower)
        return count
    
    def _assess_completeness(self, text: str) -> float:
        """Assess how complete the proposal appears to be"""
        completion_indicators = [
            'objective', 'goal', 'approach', 'method', 'timeline', 'budget',
            'team', 'experience', 'qualification', 'deliverable', 'outcome',
            'benefit', 'advantage', 'solution', 'strategy', 'plan'
        ]
        
        text_lower = text.lower()
        found_indicators = sum(1 for indicator in completion_indicators if indicator in text_lower)
        
        # Score based on coverage of key sections
        completeness = min(1.0, found_indicators / len(completion_indicators))
        return completeness
    
    def _assess_professionalism(self, text: str) -> float:
        """Assess the professional quality of the writing"""
        # Professional indicators
        professional_phrases = [
            'we propose', 'our team', 'our experience', 'we will', 'we have',
            'pleased to', 'look forward', 'thank you', 'sincerely', 'respectfully'
        ]
        
        # Unprofessional indicators (negative scoring)
        unprofessional_indicators = [
            'definitely', 'awesome', 'super', 'totally', 'basically',
            'stuff', 'things', 'whatever', 'kinda', 'sorta'
        ]
        
        text_lower = text.lower()
        
        professional_count = sum(1 for phrase in professional_phrases if phrase in text_lower)
        unprofessional_count = sum(1 for indicator in unprofessional_indicators if indicator in text_lower)
        
        # Calculate score (0.5 baseline, +0.1 for each professional phrase, -0.1 for unprofessional)
        score = 0.5 + (professional_count * 0.1) - (unprofessional_count * 0.1)
        return max(0.0, min(1.0, score))
    
    def _analyze_with_spacy(self, text: str) -> Dict[str, Any]:
        """Advanced analysis using spaCy when available"""
        try:
            if self.nlp is None:
                return {}
            
            doc = self.nlp(text)
            
            # Entity recognition
            entities = [(ent.label_, ent.text) for ent in doc.ents]
            
            # POS tagging statistics
            pos_counts = {}
            for token in doc:
                pos = token.pos_
                pos_counts[pos] = pos_counts.get(pos, 0) + 1
            
            # Calculate linguistic complexity
            avg_token_length = sum(len(token.text) for token in doc) / len(doc) if len(doc) > 0 else 0
            
            return {
                'entities': entities,
                'pos_distribution': pos_counts,
                'avg_token_length': avg_token_length,
                'linguistic_complexity': min(1.0, avg_token_length / 10.0)  # Normalized
            }
            
        except Exception as e:
            logger.warning(f"SpaCy analysis failed: {str(e)}")
            return {}
    
    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall quality score from individual metrics"""
        try:
            # Weight different aspects
            weights = {
                'readability_score': 0.2,
                'completeness_score': 0.3,
                'professional_score': 0.2,
                'technical_terms_count': 0.1,
                'word_count': 0.1,
                'linguistic_complexity': 0.1
            }
            
            score = 0.0
            total_weight = 0.0
            
            # Readability
            if 'readability_score' in metrics:
                score += metrics['readability_score'] * weights['readability_score']
                total_weight += weights['readability_score']
            
            # Completeness
            if 'completeness_score' in metrics:
                score += metrics['completeness_score'] * weights['completeness_score']
                total_weight += weights['completeness_score']
            
            # Professionalism
            if 'professional_score' in metrics:
                score += metrics['professional_score'] * weights['professional_score']
                total_weight += weights['professional_score']
            
            # Technical terms (normalize to 0-1)
            if 'technical_terms_count' in metrics:
                tech_score = min(1.0, metrics['technical_terms_count'] / 10.0)
                score += tech_score * weights['technical_terms_count']
                total_weight += weights['technical_terms_count']
            
            # Word count (optimal range 200-1000 words)
            if 'word_count' in metrics:
                word_count = metrics['word_count']
                if word_count < 50:
                    word_score = 0.2  # Too short
                elif word_count < 200:
                    word_score = 0.6  # Short but acceptable
                elif word_count < 1000:
                    word_score = 1.0  # Good length
                elif word_count < 2000:
                    word_score = 0.8  # Long but acceptable
                else:
                    word_score = 0.5  # Too long
                
                score += word_score * weights['word_count']
                total_weight += weights['word_count']
            
            # Linguistic complexity (if available from spaCy)
            if 'linguistic_complexity' in metrics:
                score += metrics['linguistic_complexity'] * weights['linguistic_complexity']
                total_weight += weights['linguistic_complexity']
            
            # Normalize score
            if total_weight > 0:
                final_score = score / total_weight
            else:
                final_score = 0.5  # Default
            
            return max(0.0, min(1.0, final_score))
            
        except Exception as e:
            logger.error(f"Quality score calculation error: {str(e)}")
            return 0.5