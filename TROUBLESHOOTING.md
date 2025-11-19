# 🔧 Gemini AI Troubleshooting Guide

## ✅ What We Fixed

### 1. **CRITICAL FIX: Wrong Model Name**
- **Problem**: Code was using `gemini-1.5-flash` which doesn't exist in v1 API
- **Error**: `404 NOT_FOUND - models/gemini-1.5-flash is not found for API version v1`
- **Solution**: Updated to `gemini-2.5-flash` (latest stable model)
- **Status**: ✅ **FIXED** - Model now works (verified with local tests)

### 2. **API Endpoint**
- **Old**: `v1beta/gemini-pro` ❌
- **New**: `v1/gemini-2.5-flash` ✅
- **Status**: ✅ **FIXED**

### 3. **Environment Variables**
- **GEMINI_API_KEY**: Configured in Vercel ✅
- **Verified**: Health endpoint shows `gemini_api_configured: true` ✅
- **Key Preview**: `AIzaSyBQBU...` ✅

## 🔍 Current Status

### What's Working:
- ✅ Gemini API key is valid (tested locally)
- ✅ Model `gemini-2.5-flash` works perfectly (tested with quick_test.py)
- ✅ Environment variable is set in Vercel
- ✅ OCR extraction working
- ✅ Regex fallback working

### What's NOT Working:
- ❌ AI extraction in Vercel serverless function
- ❌ System keeps falling back to regex
- ❌ No visible error in response (need to check function logs)

## 📊 Next Steps to Debug

### Step 1: Check Vercel Function Logs

1. Go to: https://vercel.com/karan-bhatis-projects-01ae0c63/ai-invoice-automation
2. Click on the latest deployment
3. Click on "Functions" tab
4. Find `/api/process` function
5. Click "View Logs"
6. Upload an invoice via the web UI or API
7. Look for these log messages:

```
Using Gemini API with key: AIzaSyBQBU...
OCR extracted XXX characters of text
First 200 chars: ...
Request URL: https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash...
Payload size: XXXX chars
Gemini API Status: XXX
```

### Step 2: Common Issues to Look For

#### Issue A: Timeout (20 seconds)
**Log will show**: `AI extraction failed: Request timeout after 20 seconds`

**Possible causes**:
- Vercel function timeout (max 10 seconds on Hobby plan)
- Network latency to Gemini API
- Large OCR text causing slow AI processing

**Solutions**:
- Reduce `maxOutputTokens` from 800 to 400
- Truncate OCR text before sending to AI (e.g., first 2000 chars)
- Upgrade to Vercel Pro (60 second timeout)

#### Issue B: API Key Not Available in Function
**Log will show**: `No GEMINI_API_KEY found, using fallback`

**Solutions**:
- Redeploy after adding environment variable
- Check environment variable scope (Production vs Preview vs Development)
- Ensure no typos in variable name

#### Issue C: Rate Limiting
**Log will show**: `Gemini API Status: 429`

**Solutions**:
- Wait a few minutes and try again
- Implement retry logic with exponential backoff
- Check Gemini API quotas in Google Cloud Console

#### Issue D: Vercel Function Memory Limit
**Log will show**: Process killed or memory errors

**Solutions**:
- Reduce payload size
- Optimize imports (only import what's needed)
- Upgrade Vercel plan for more memory

#### Issue E: Request/Response Size Limit
**Symptoms**: Large invoices fail, small ones work

**Solutions**:
- Limit OCR text to first 3000 characters
- Compress/summarize OCR output before sending to AI

### Step 3: Test Locally

Run the test scripts we created:

```powershell
# Test 1: Basic Gemini API connection
python test_gemini.py

# Test 2: Quick invoice extraction
python quick_test.py
```

Both should show ✅ SUCCESS if your API key is working.

### Step 4: Check Vercel Environment Variables

1. Go to: https://vercel.com/karan-bhatis-projects-01ae0c63/ai-invoice-automation/settings/environment-variables
2. Verify `GEMINI_API_KEY` exists
3. Make sure it's enabled for:
   - ✅ Production
   - ✅ Preview
   - ✅ Development (optional)
4. Verify the value starts with `AIzaSy...` (no extra spaces/quotes)
5. After any changes, **redeploy**

## 🧪 Available Models (v1 API)

Tested and available:
- `gemini-2.5-flash` ✅ (CURRENT - best balance of speed/quality)
- `gemini-2.5-pro` ✅ (highest quality, slower)
- `gemini-2.0-flash` ✅ (older version)
- `gemini-2.0-flash-lite` ✅ (faster, less capable)

NOT available:
- `gemini-1.5-flash` ❌ (doesn't exist in v1 API)
- `gemini-pro` ❌ (only in v1beta)

## 📝 How to Get Detailed Logs

### Option 1: Vercel Dashboard (Recommended)
1. Visit deployment page
2. Functions tab → /api/process
3. Real-time logs appear when requests are made

### Option 2: Vercel CLI
```powershell
vercel logs [deployment-url] --follow
```

### Option 3: Add More Console Logs
The code now includes extensive logging:
- API key presence check
- OCR text length and preview
- Request URL and payload size
- Response status and headers
- Detailed error types (timeout, request error, JSON parse error, etc.)

## 🎯 Quick Verification Checklist

- [ ] `gemini-2.5-flash` model name in code
- [ ] GEMINI_API_KEY in Vercel environment variables
- [ ] Environment variable scope includes "Production"
- [ ] Redeployed after adding/changing variables
- [ ] Generative Language API enabled in Google Cloud Console
- [ ] API key tested locally with test_gemini.py
- [ ] Checked function logs for actual error message
- [ ] No typos in environment variable name

## 💡 Alternative: Switch to OpenAI

If Gemini continues to have issues in Vercel, we can switch to OpenAI GPT:

**Pros**:
- More stable/reliable
- Better documentation
- Faster response times
- Better JSON formatting

**Cons**:
- Costs ~$0.15 per 1000 API calls
- Requires credit card for API access

**To switch**, modify `extract_with_ai()` in `api/processor.py` to use:
```
https://api.openai.com/v1/chat/completions
```

## 📞 Final Notes

The AI integration is **fully coded and working locally**. The issue is isolated to the Vercel serverless environment. Most likely causes:

1. **Timeout** (Vercel Hobby plan = 10 sec max)
2. **Environment variable not loaded** (rare but possible)
3. **Network/firewall issue** (very unlikely)

**Check the function logs** - they will tell us exactly what's failing!
