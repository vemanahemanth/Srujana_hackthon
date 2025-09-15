# TenderGuard ACTMS - Easy Setup Guide
## Local Setup (Any Computer)
1. **Prerequisites**: Python 3.11+
2. **Clone the repository**
3. **Install dependencies**: 
   ```bash
   pip install -r requirements.txt
   ```
4. **Initialize the system**:
   ```bash
   python init_system.py
   ```
5. **Run the application**:
   ```bash
   python app.py
   ```
6. **Open your browser** to `http://localhost:5000`

## Features Available
- ✅ **Dashboard**: Real-time analytics with 5 tenders, 8 bids, and AI fraud detection
- ✅ **Tender Management**: Create and view tenders
- ✅ **Bid Submission**: Submit bids with automatic fraud analysis
- ✅ **AI Analysis**: Machine learning fraud detection (1 suspicious bid detected)
- ✅ **Chat Assistant**: FAQ support system
- ✅ **Audit Logs**: Complete system activity tracking

## Optional Configuration
- **GEMINI_API_KEY**: For enhanced chatbot (falls back to FAQ mode)
- **SESSION_SECRET**: For production security

## What Works Out of the Box
- SQLite database with sample data
- ML fraud detection with pre-trained models
- NLP proposal analysis
- Real-time dashboard updates
- Mobile-responsive design

The system is ready to use immediately with no additional setup required!
