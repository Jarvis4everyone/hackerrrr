# Login Issue Fix

## The Problem

Login wasn't working because authentication credentials weren't being loaded from environment variables in Docker/Render.

## The Fix

Updated `app/config.py` to:
1. **First check environment variables** (AUTH_USERNAME, AUTH_PASSWORD)
2. **Then fallback to .env file** (for local development)

## How to Set Credentials in Render

### Option 1: Using Render Dashboard (Recommended)

1. Go to Render Dashboard → **hackerrrr-backend** service
2. Go to **Environment** tab
3. Add these environment variables:

```
AUTH_USERNAME=your_username
AUTH_PASSWORD=your_password
```

4. Click **Save Changes**
5. The service will automatically redeploy

### Option 2: Using render.yaml

The `render.yaml` file now includes placeholders for these variables. You still need to set the actual values in the Render dashboard.

## Default Credentials

If no environment variables are set, the default credentials are:
- Username: `admin`
- Password: `admin`

**⚠️ IMPORTANT:** Change these in production!

## Testing

After setting the environment variables:

1. Wait for the backend service to redeploy
2. Try logging in with your credentials
3. Check backend logs if login still fails (they show what username/password is expected)

## Local Development

For local development, you can still use `.env` file:
```
Username = your_username
Password = your_password
```

Or set environment variables:
```bash
export AUTH_USERNAME=your_username
export AUTH_PASSWORD=your_password
```

