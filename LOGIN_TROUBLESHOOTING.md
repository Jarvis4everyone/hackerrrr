# Login Troubleshooting Guide

## Current Issue

Login says "incorrect password" but credentials seem correct.

## Root Cause

The backend is using **default credentials** (`admin`/`admin`) because environment variables aren't set in Render.

## Solution: Set Environment Variables in Render

### Step 1: Go to Render Dashboard
1. Open Render Dashboard
2. Click on **hackerrrr-backend** service

### Step 2: Set Environment Variables
1. Go to **Environment** tab
2. Add these two environment variables:

```
AUTH_USERNAME=Shresth
AUTH_PASSWORD=hackur
```

**Important:** 
- Use the exact username and password you want to use
- Case-sensitive!
- No spaces around the `=`

### Step 3: Save and Wait
1. Click **Save Changes**
2. Wait for the service to redeploy (1-2 minutes)
3. Check the logs - you should see:
   ```
   Auth username loaded: Shresth
   Auth password loaded: ********
   ```

## Verify It's Working

After redeploying:

1. **Check Backend Logs** in Render:
   - Look for "Auth username loaded: Shresth"
   - This confirms the environment variable is set

2. **Try Login Again**:
   - Username: `Shresth`
   - Password: `hackur`
   - Should work now!

## If Still Not Working

### Check Backend Logs
When you try to login, the backend logs will show:
```
Login attempt - Username: Shresth
Expected username: Shresth
Username match: True/False
Password match: True/False
```

This will tell you exactly what's wrong.

### Common Issues

1. **Environment variables not set**: Backend uses defaults (`admin`/`admin`)
2. **Case sensitivity**: `Shresth` ≠ `shresth`
3. **Extra spaces**: Check for spaces in the environment variable values
4. **Backend not redeployed**: Changes only take effect after redeploy

## Default Credentials

If no environment variables are set, defaults are:
- Username: `admin`
- Password: `admin`

## Testing

You can test with default credentials first:
- Username: `admin`
- Password: `admin`

If this works, then the issue is just the environment variables not being set.

