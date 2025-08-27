# BSE Monitor - AI PDF Analysis Setup Guide

## 🤖 AI PDF Analysis Feature

The BSE Monitor application now includes AI-powered PDF analysis using Google's Gemini API. This feature can analyze corporate announcements, financial reports, and other PDF documents to provide comprehensive investment insights.

## 🚀 Setup Instructions

### 1. Get a Gemini API Key

1. Visit [Google AI Studio](https://ai.google.dev/tutorials/get_started_web)
2. Click "Get API Key" 
3. Create a new project or select an existing one
4. Generate your API key

### 2. Configure the API Key

Add your Gemini API key to the `.env` file:

```env
# AI/PDF Analysis Configuration
GEMINI_API_KEY="your-actual-gemini-api-key-here"
GEMINI_MODEL="gemini-1.5-flash"
```

### 3. Install Dependencies

The required AI dependencies should already be installed. If not, run:

```bash
pip install google-generativeai PyPDF2 pdfplumber Pillow pdf2image
```

### 4. Test the Configuration

Run the AI configuration test:

```bash
python test_ai.py
```

You should see:
```
🎯 All tests passed! AI PDF analysis should work correctly.
```

## 📊 Using AI PDF Analysis

### From the Dashboard

1. **Start the Application**:
   ```bash
   python app.py
   ```

2. **Access the Dashboard**:
   - Go to `http://localhost:5000`
   - Log in with your credentials

3. **Upload a PDF**:
   - Click the "🤖 AI PDF Analysis" button
   - Select a PDF file (corporate announcements, financial reports, etc.)
   - Optionally enter a BSE scrip code for enhanced analysis
   - Click "🚀 Analyze with AI"

4. **View Results**:
   - The AI will analyze the document and provide:
     - **Company Information**: Name, scrip code, document type
     - **Financial Summary**: Revenue, profit, EPS, debt, cash flow
     - **Investment Analysis**: BUY/SELL/HOLD recommendation, price target, sentiment
     - **Market Impact**: Public perception, catalyst impact, price momentum
     - **Summary**: Key takeaways and TL;DR

## 🎯 What the AI Analyzes

The AI provides comprehensive analysis including:

- **📈 Financial Metrics**: Revenue, profit, EPS, debt ratios
- **🎯 Investment Recommendation**: BUY/SELL/HOLD with reasoning
- **💰 Price Targets**: Analyst price targets if mentioned
- **📊 Sentiment Analysis**: POSITIVE/NEGATIVE/NEUTRAL market sentiment
- **🚀 Catalyst Impact**: How announcements might affect stock price
- **⚠️ Risk Assessment**: Risk factors and opportunities
- **🧠 Market Psychology**: Expected public and institutional reaction

## 🔧 Troubleshooting

### Common Issues

1. **"AI service unavailable" Error**:
   - Check that `GEMINI_API_KEY` is set in `.env`
   - Verify the API key is valid
   - Run `python test_ai.py` to diagnose

2. **"Invalid PDF format" Error**:
   - Ensure the file is a valid PDF
   - Check file size (large files may timeout)
   - Try with a different PDF

3. **"Rate limit exceeded" Error**:
   - Wait a few minutes before trying again
   - Gemini API has rate limits for free tier

4. **"API key invalid" Error**:
   - Double-check your API key in `.env`
   - Ensure there are no extra quotes or spaces
   - Regenerate the API key if needed

### Test Commands

```bash
# Test AI configuration
python test_ai.py

# Test application startup
python app.py

# Check health endpoint
curl http://localhost:5000/health
```

## 📝 Supported File Types

- **PDF Files**: Corporate announcements, annual reports, quarterly results
- **Content Types**: Financial reports, regulatory filings, press releases
- **Languages**: Primarily English, with some support for other languages

## 🔒 Security & Privacy

- **API Keys**: Stored securely in `.env` file (never commit to version control)
- **File Processing**: PDFs are temporarily uploaded to Gemini API and automatically deleted
- **Data Retention**: No analysis data is stored permanently on external servers

## 🚀 Performance Tips

1. **Use gemini-1.5-flash**: Faster and more cost-effective than gemini-1.5-pro
2. **Optimize PDF Size**: Smaller files process faster
3. **Batch Processing**: Analyze multiple documents in sequence rather than parallel

## 💡 Example Use Cases

- **Earnings Analysis**: Upload quarterly results for automated analysis
- **IPO Evaluation**: Analyze prospectus documents for investment insights
- **Regulatory Filings**: Get quick summaries of compliance documents
- **Market Research**: Extract key insights from research reports

## 🆘 Support

If you encounter issues:

1. Check the application logs for specific error messages
2. Run the test script: `python test_ai.py`
3. Verify your API key at [Google AI Studio](https://ai.google.dev/)
4. Check the [Gemini API documentation](https://ai.google.dev/gemini-api/docs)

## 🔗 Useful Links

- [Google AI Studio](https://ai.google.dev/tutorials/get_started_web)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [Python Quickstart Guide](https://ai.google.dev/gemini-api/docs/quickstart?lang=python)

---

**Note**: The AI analysis is for informational purposes only and should not be considered as financial advice. Always consult with a qualified financial advisor before making investment decisions.