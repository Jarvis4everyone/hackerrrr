# Render Environment Variables Setup

## Backend Service (hackerrrr-backend)

Your backend is live at: **https://hackerrrr-backend.onrender.com/**

### Environment Variables (Already Set):
- `HOST=0.0.0.0`
- `PORT=8000`
- `DEBUG=False`
- `MONGODB_URL=your_mongodb_connection_string` (set this)
- `MONGODB_DB_NAME=remote_script_server`

## Frontend Service (hackerrrr-frontend)

### Required Environment Variable:

**Set this in Render Dashboard → Frontend Service → Environment Variables:**

```
VITE_API_URL=https://hackerrrr-backend.onrender.com
```

**Important:** 
- This must be set BEFORE building the frontend
- After setting, you need to **rebuild/redeploy** the frontend service
- The frontend code will auto-detect if this is not set, but it's better to set it explicitly

## Steps to Fix Frontend:

1. Go to Render Dashboard
2. Click on your **hackerrrr-frontend** service
3. Go to **Environment** tab
4. Add environment variable:
   - Key: `VITE_API_URL`
   - Value: `https://hackerrrr-backend.onrender.com`
5. Click **Save Changes**
6. Go to **Manual Deploy** → **Deploy latest commit** (or it will auto-deploy)

## Verify It's Working:

After redeploying frontend:
1. Open your frontend URL (e.g., `https://hackerrrr-frontend.onrender.com`)
2. Open browser console (F12)
3. Check Network tab - API calls should go to `https://hackerrrr-backend.onrender.com`
4. Try logging in - should work without CORS errors

## Auto-Detection Fallback:

If `VITE_API_URL` is not set, the frontend code will try to auto-detect:
- If frontend is on `hackerrrr-frontend.onrender.com`
- It will use `hackerrrr-backend.onrender.com`

But it's **recommended to set it explicitly** for reliability.

