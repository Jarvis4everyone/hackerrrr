# Render Setup Guide

## Auto-Detection

Yes! Render will automatically detect Docker when you:
1. Select **"Docker"** as the environment type
2. Provide the Dockerfile path (e.g., `Dockerfile.backend` or `Dockerfile.frontend`)

Render will then:
- Build the Docker image using the specified Dockerfile
- Run the container automatically
- Handle port mapping and routing

## Quick Setup Steps

### Option 1: Using Blueprint (Recommended)

1. Go to Render Dashboard → **New** → **Blueprint**
2. Connect your GitHub repository: `Jarvis4everyone/hackerrrr`
3. Render will automatically detect `render.yaml` and create both services
4. Set the required environment variables in the dashboard:
   - **Backend**: `MONGODB_URL` (your MongoDB connection string)
   - **Frontend**: `VITE_API_URL` (your backend service URL)

### Option 2: Manual Setup

#### Backend Service

1. Go to Render Dashboard → **New** → **Web Service**
2. Connect repository: `Jarvis4everyone/hackerrrr`
3. Configure:
   - **Name**: `hackerrrr-backend`
   - **Environment**: **Docker** ← This enables auto-detection
   - **Dockerfile Path**: `Dockerfile.backend`
   - **Docker Context**: `.`
4. Add environment variables:
   ```
   HOST=0.0.0.0
   PORT=8000
   DEBUG=False
   MONGODB_URL=your_mongodb_connection_string
   MONGODB_DB_NAME=remote_script_server
   ```
5. Click **Create Web Service**

#### Frontend Service

1. Go to Render Dashboard → **New** → **Web Service**
2. Connect the same repository
3. Configure:
   - **Name**: `hackerrrr-frontend`
   - **Environment**: **Docker** ← This enables auto-detection
   - **Dockerfile Path**: `Dockerfile.frontend`
   - **Docker Context**: `.`
4. Add environment variable:
   ```
   VITE_API_URL=https://hackerrrr-backend.onrender.com
   ```
   (Replace with your actual backend URL)
5. Click **Create Web Service**

## Environment Variables Reference

### Backend (.env or Render Dashboard)

```env
HOST=0.0.0.0
PORT=8000
DEBUG=False
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DB_NAME=remote_script_server
```

### Frontend (Render Dashboard only - for build time)

```env
VITE_API_URL=https://hackerrrr-backend.onrender.com
```

## Important Notes

1. **Docker Auto-Detection**: When you select "Docker" as the environment, Render automatically:
   - Detects the Dockerfile
   - Builds the Docker image
   - Runs the container
   - Maps ports automatically

2. **Environment Variables**: 
   - Set them in Render Dashboard → Environment Variables
   - Don't commit `.env` files with sensitive data
   - Use Render's environment variable UI for production

3. **Build Args**: The frontend Dockerfile uses `VITE_API_URL` as a build argument. Make sure to set this in Render dashboard before the first build.

4. **Service URLs**: After deployment, Render provides URLs like:
   - Backend: `https://hackerrrr-backend.onrender.com`
   - Frontend: `https://hackerrrr-frontend.onrender.com`

5. **Free Tier**: Services spin down after 15 minutes of inactivity. First request may take 30-60 seconds.

## Troubleshooting

### Docker Not Detected?
- Make sure you selected **"Docker"** as the environment type
- Verify the Dockerfile path is correct
- Check that Dockerfile exists in the repository

### Build Fails?
- Check build logs in Render dashboard
- Verify all environment variables are set
- Ensure Dockerfile syntax is correct

### Frontend Can't Connect to Backend?
- Verify `VITE_API_URL` is set correctly
- Check backend service is running
- Ensure CORS is configured (already set to allow all origins)

