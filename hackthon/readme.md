# Overview

ACTMS (Anti-Corruption Tender Management System) is a comprehensive web application built to manage government tenders with AI-powered fraud detection capabilities. The system provides a complete solution for tender creation, bid submission, real-time analytics, and intelligent anomaly detection to ensure transparency and prevent corruption in the tender process.

The application features a modern glassmorphism UI design with a monochrome color scheme, real-time dashboard analytics, AI-powered fraud detection using machine learning, and an integrated chatbot for user assistance.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
The frontend is built using traditional server-side rendering with Flask and Jinja2 templates. The UI follows a glassmorphism design system with a monochrome color palette (black, gray, white) and frosted glass effects. The architecture includes:

- **Template Structure**: Modular template system with base.html for common layout and specialized templates for each feature
- **Component System**: Reusable macros for icons and glass components in partials/icons.html
- **JavaScript Architecture**: Global utilities in static/js/global.js handling animations, API calls, and common functionality
- **CSS Design System**: Comprehensive design system in static/styles/global.css with CSS variables for consistent styling
- **Progressive Enhancement**: JavaScript enhances the experience but the application works without it

## Backend Architecture
The backend follows a service-oriented architecture built on Flask with modular services:

- **Flask Application**: Main application in app.py with RESTful API endpoints
- **Service Layer**: Modular services in the services/ directory for separation of concerns
- **Database Service**: SQLite-based data persistence with schema management
- **ML Service**: Machine learning fraud detection using Isolation Forest algorithm
- **NLP Service**: Natural language processing for proposal analysis using spaCy
- **File Handler**: Secure file upload and processing with validation
- **Chatbot Service**: AI assistant with Gemini API integration and FAQ fallback

## Data Storage
The system uses SQLite for simplicity and portability:

- **Database**: Single SQLite file (actms.db) containing all application data
- **Schema**: Tables for tenders, bids, audit logs, and system tracking
- **Initialization**: Automated database setup with sample data via init_system.py
- **Data Integrity**: Foreign key constraints and data validation at service level

## Authentication and Security
Security is implemented through multiple layers:

- **Session Management**: Flask sessions with configurable secret keys
- **File Upload Security**: Comprehensive file validation with extension, MIME type, and signature checking
- **Input Validation**: Server-side validation for all user inputs
- **Audit Logging**: Complete audit trail for all system activities
- **CORS Configuration**: Controlled cross-origin resource sharing

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web framework for backend API and routing
- **Flask-CORS**: Cross-origin resource sharing configuration
- **Werkzeug**: WSGI utilities for secure file handling

## AI and Machine Learning
- **scikit-learn**: Machine learning library for Isolation Forest fraud detection
- **numpy**: Numerical computing for ML operations
- **pandas**: Data manipulation and analysis
- **joblib**: Model serialization and loading
- **spaCy**: Natural language processing for proposal analysis

## Optional AI Services
- **Google Gemini API**: Advanced chatbot functionality (falls back to FAQ system if not available)
- **OpenAI**: Alternative AI service integration capability

## Development and Deployment
- **python-dotenv**: Environment variable management for configuration
- **SQLite**: Embedded database requiring no additional setup

The system is designed to work out-of-the-box with minimal configuration, automatically falling back to local alternatives when external services are unavailable.
