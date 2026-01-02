# Agora "Invalid Vendor Key" Error - Troubleshooting Guide

## Why This Error Happens

The error `invalid vendor key, can not find appid` occurs when Agora's servers cannot validate your App ID. Even if your credentials are correct, there are several reasons this can happen:

### 1. **Token Mismatch (Most Common)**

**Problem**: The backend is using a **fallback temp token** that was generated for a different App ID (or is invalid/expired).

**Why**: If `agora-token-builder` is not installed in your deployed backend, the system falls back to using `AGORA_TEMP_TOKEN` from environment variables. This temp token doesn't match your actual App ID.

**Solution**:
- Ensure `agora-token-builder` is installed in your backend
- Check backend logs for: `"agora-token-builder not installed"`
- If you see this, the backend needs to be rebuilt with `agora-token-builder` installed

### 2. **App ID Not Enabled for RTC**

**Problem**: Your App ID exists but isn't enabled for Real-Time Communication (RTC) usage.

**Solution**:
1. Go to https://console.agora.io/
2. Select your project
3. Go to **Features** or **Products** section
4. Ensure **Real-Time Communication (RTC)** is enabled
5. Some projects need explicit activation for RTC

### 3. **Region/Data Center Mismatch**

**Problem**: Your App ID might be from a different region, and the SDK is trying to connect to the wrong data center.

**Solution**:
- Check your Agora Console project settings
- Verify the region/data center matches your usage
- Agora automatically routes to the correct region, but misconfiguration can cause issues

### 4. **Token Generation Error**

**Problem**: Token is being generated incorrectly due to:
- Wrong role values
- Invalid timestamp
- Certificate mismatch

**Solution**: Check backend logs for token generation errors. The improved logging will show:
- Whether `agora-token-builder` is installed
- App ID and Certificate being used
- Any errors during token generation

### 5. **Expired or Invalid Certificate**

**Problem**: The App Certificate might be:
- Expired
- Regenerated (old certificate no longer valid)
- Copied incorrectly (extra spaces, wrong characters)

**Solution**:
- Verify the certificate in Agora Console matches exactly
- Check for any extra spaces or hidden characters
- Regenerate the certificate if needed

## How to Fix

### Step 1: Verify Backend Installation

Check if `agora-token-builder` is installed in your deployed backend:

1. Check Render backend logs for:
   ```
   [Agora] agora-token-builder not installed. Using fallback token generation.
   ```

2. If you see this, the backend needs to be rebuilt. The package is in `requirements.txt`, so a rebuild should install it.

### Step 2: Verify Environment Variables

In your Render backend service, ensure these are set correctly:

```
AGORA_APP_ID=7b3640aaf0394f8d809829db4abbe902
AGORA_APP_CERTIFICATE=15b63fe200b44aa5a2428ace9d857ba4
```

**Important**: Do NOT set `AGORA_TEMP_TOKEN` unless you're using it as a temporary workaround. The system should generate tokens dynamically.

### Step 3: Check Agora Console

1. **Verify App ID**: 
   - Go to https://console.agora.io/
   - Select your project
   - Copy the App ID and verify it matches exactly

2. **Verify Certificate**:
   - In the same project, go to **Config** or **Security**
   - Copy the Primary Certificate
   - Verify it matches exactly (no spaces, correct characters)

3. **Enable RTC**:
   - Check if RTC is enabled for your project
   - Some projects require explicit activation

### Step 4: Check Backend Logs

After starting a stream, check your backend logs for:

```
[Agora] Generating token - App ID: 7b3640aa..., Cert: 15b63fe2..., Channel: ...
[Agora] ✅ Token generated successfully
```

If you see:
```
[Agora] ❌ agora-token-builder NOT INSTALLED!
```

Then the backend needs to be rebuilt to install the package.

### Step 5: Test Token Generation

You can test if token generation works by checking the backend API response. When you start a stream, the response should include:

```json
{
  "agora": {
    "channel_name": "PC-001_camera",
    "token": "007eJxTY...",  // Should be a long token string
    "uid": 0,
    "app_id": "7b3640aaf0394f8d809829db4abbe902"
  }
}
```

If the token looks like the temp token from config, then token generation isn't working.

## Common Issues

### Issue: "agora-token-builder not installed"

**Symptom**: Backend logs show fallback token usage

**Fix**: 
1. Ensure `requirements.txt` includes `agora-token-builder>=1.0.0`
2. Rebuild the backend service on Render
3. Verify the package is installed in the container

### Issue: Token looks correct but still fails

**Possible Causes**:
1. App ID not enabled for RTC in Agora Console
2. Certificate regenerated but backend not updated
3. Region/data center mismatch

**Fix**:
1. Verify RTC is enabled in Agora Console
2. Update certificate in backend environment variables
3. Check Agora project region settings

### Issue: Works locally but not on Render

**Possible Causes**:
1. Environment variables not set in Render
2. `agora-token-builder` not installed in Docker image
3. Different Python version causing import issues

**Fix**:
1. Verify all environment variables are set in Render dashboard
2. Check Docker build logs for `agora-token-builder` installation
3. Ensure Python 3.11 is used (as specified in Dockerfile)

## Verification Checklist

- [ ] `agora-token-builder` is in `requirements.txt`
- [ ] Backend logs show "Token generated successfully" (not fallback)
- [ ] App ID is exactly 32 hex characters
- [ ] Certificate is exactly 32 hex characters
- [ ] Environment variables are set in Render
- [ ] RTC is enabled in Agora Console
- [ ] No extra spaces in credentials
- [ ] Backend service has been rebuilt after adding credentials

## Still Not Working?

If after checking all of the above it still doesn't work:

1. **Check Backend Logs**: Look for detailed Agora token generation logs
2. **Verify in Agora Console**: Ensure the project is active and RTC-enabled
3. **Test with Agora's Token Builder Tool**: Use Agora's online token generator to verify your credentials work
4. **Contact Agora Support**: If credentials are definitely correct, there might be an account/project issue

## Quick Test

To quickly test if your credentials work:

1. Go to Agora Console
2. Use their token generator tool
3. Enter your App ID and Certificate
4. Generate a test token
5. If this fails, the issue is with the credentials themselves
6. If this works, the issue is with how tokens are being generated in the backend

