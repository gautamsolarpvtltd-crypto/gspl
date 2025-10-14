# Gautam Solar Portal - Certificate Management

## ✅ Setup Complete!

### 📁 Files Created:
1. portal.html - Main public portal page
2. assets/cert-links.json - Certificate links configuration
3. PORTAL_README.md - This file

## 🔧 How to Update Certificate Links:

### Step 1: Upload files to Google Drive
1. Go to Google Drive
2. Upload your certificate PDF files
3. Right-click each file → "Get link"
4. Change to "Anyone with the link"
5. Copy the link

### Step 2: Edit assets/cert-links.json
1. Open: assets/cert-links.json
2. Find the section you want to update
3. Replace "YOUR_FILE_ID_XX" with your actual Google Drive link
4. Save the file

### Example:
```json
{
  "label": "GST Certificate",
  "url": "https://drive.google.com/file/d/1AbC123XyZ_RealFileID/view"
}
```

### Step 3: Refresh browser
- Press Ctrl+F5 (hard refresh) to see changes

## 📦 File Structure:
```
gautam-solar-portal/
├── app.py
├── portal.html
├── assets/
│   └── cert-links.json   ← Edit this file to update links
└── PORTAL_README.md
```

## 🚀 Testing:
1. Run: python app.py
2. Open: http://127.0.0.1:5000/portal
3. You should see all download buttons
4. Click any button to test (will go to Google Drive placeholder)

## 💡 Tips:
- All URLs marked as "YOUR_FILE_ID_XX" are placeholders
- Replace them with real Google Drive links
- You can also use direct URLs to PDF files on your server
- JSON file must be valid (check commas and brackets)

## 🆘 Troubleshooting:
- If buttons don't appear: Check browser console (F12)
- If JSON error: Validate at jsonlint.com
- If 404 error: Make sure assets/ folder exists
