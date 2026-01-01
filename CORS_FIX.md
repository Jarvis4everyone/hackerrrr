# CORS Error Fix

## The Problem

1. **CORS Error**: FastAPI's CORSMiddleware doesn't allow `allow_credentials=True` with `allow_origins=["*"]`
2. **Wrong Backend URL**: Frontend is using placeholder URL `your-backend-service.onrender.com`

## Solutions Applied

### 1. Fixed CORS Configuration
- Updated `app/main.py` to handle CORS properly
- When using `["*"]`, credentials are disabled (which is fine for most cases)
- If you need credentials, set specific origins in environment variable

### 2. Fixed Frontend API URL Detection
- Updated frontend to automatically detect backend URL on Render
- If `VITE_API_URL` is not set, it will try to construct the backend URL from the frontend URL
- For Render: `hackerrrr-frontend.onrender.com` → `hackerrrr-backend.onrender.com`

## What You Need to Do

### Option 1: Set VITE_API_URL (Recommended)
In Render Dashboard → Frontend Service → Environment Variables:
```
VITE_API_URL=https://hackerrrr-backend.onrender.com
```
(Replace with your actual backend URL)

Then **rebuild** the frontend service.

### Option 2: Let Frontend Auto-Detect
The code now automatically detects the backend URL if:
- Frontend is on `hackerrrr-frontend.onrender.com`
- Backend is on `hackerrrr-backend.onrender.com`

Just redeploy the frontend with the updated code.

## Testing

After deploying:
1. Check browser console - CORS errors should be gone
2. Check Network tab - API calls should go to correct backend URL
3. Login should work

## If Still Having Issues

1. **Check Backend CORS**: Backend should allow all origins now (without credentials)
2. **Check Frontend URL**: Make sure frontend is calling the correct backend URL
3. **Check Backend is Running**: Verify backend service is up and accessible
4. **Check Environment Variables**: Ensure `VITE_API_URL` is set correctly if using Option 1

