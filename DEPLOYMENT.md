# Deployment Guide for Render

This guide explains how to deploy the hackerrrr application on Render using Docker.

## Prerequisites

1. GitHub account with the repository: `https://github.com/Jarvis4everyone/hackerrrr.git`
2. Render account (sign up at https://render.com)
3. MongoDB database (can use MongoDB Atlas or Render's MongoDB service)

## Architecture

- **Backend**: FastAPI application running on port 8000
- **Frontend**: React application served via Nginx on port 3000
- **Database**: MongoDB (external service)

## Deployment Steps

### 1. Deploy Backend Service

1. Go to Render Dashboard → New → Web Service
2. Connect your GitHub repository: `Jarvis4everyone/hackerrrr`
3. Configure the service:
   - **Name**: `hackerrrr-backend`
   - **Environment**: `Docker`
   - **Dockerfile Path**: `Dockerfile.backend`
   - **Docker Context**: `.` (root directory)
   - **Plan**: Free (or choose your plan)

4. Set Environment Variables:
   - `HOST`: `0.0.0.0`
   - `PORT`: `8000`
   - `DEBUG`: `False`
   - `MONGODB_URL`: Your MongoDB connection string
   - `MONGODB_DB_NAME`: `remote_script_server` (or your preferred name)

5. Click "Create Web Service"

6. Note the backend service URL (e.g., `https://hackerrrr-backend.onrender.com`)

### 2. Deploy Frontend Service

1. Go to Render Dashboard → New → Web Service
2. Connect the same GitHub repository
3. Configure the service:
   - **Name**: `hackerrrr-frontend`
   - **Environment**: `Docker`
   - **Dockerfile Path**: `Dockerfile.frontend`
   - **Docker Context**: `.` (root directory)
   - **Plan**: Free (or choose your plan)

4. Set Environment Variables:
   - `VITE_API_URL`: Your backend service URL (e.g., `https://hackerrrr-backend.onrender.com`)

5. Click "Create Web Service"

### 3. Using render.yaml (Alternative Method)

If you prefer to use the `render.yaml` file:

1. Go to Render Dashboard → New → Blueprint
2. Connect your GitHub repository
3. Render will automatically detect `render.yaml` and create both services
4. You'll need to set the `MONGODB_URL` and `VITE_API_URL` environment variables in the Render dashboard

## Environment Variables Reference

### Backend
- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8000`)
- `DEBUG`: Debug mode (default: `False`)
- `MONGODB_URL`: MongoDB connection string (required)
- `MONGODB_DB_NAME`: Database name (default: `remote_script_server`)

### Frontend
- `VITE_API_URL`: Backend API URL (required for production build)

## Important Notes

1. **Free Tier Limitations**: Render's free tier spins down services after 15 minutes of inactivity. The first request after spin-down may take 30-60 seconds.

2. **WebSocket Support**: Render supports WebSockets, but ensure your backend URL uses `wss://` for secure WebSocket connections in production.

3. **CORS**: The backend is configured to allow all origins (`*`). For production, consider restricting this to your frontend URL.

4. **MongoDB**: Use MongoDB Atlas (free tier available) or Render's MongoDB service. Make sure your MongoDB connection string is accessible from Render's servers.

5. **Build Time**: The frontend build requires `VITE_API_URL` to be set at build time. Make sure this environment variable is set before the build starts.

## Testing Locally with Docker

```bash
# Build and run backend
docker build -f Dockerfile.backend -t hackerrrr-backend .
docker run -p 8000:8000 -e MONGODB_URL=your_mongodb_url hackerrrr-backend

# Build and run frontend
docker build -f Dockerfile.frontend --build-arg VITE_API_URL=http://localhost:8000 -t hackerrrr-frontend .
docker run -p 3000:3000 hackerrrr-frontend

# Or use docker-compose
docker-compose up
```

## Troubleshooting

### Backend Issues
- Check logs in Render dashboard
- Verify MongoDB connection string is correct
- Ensure port 8000 is exposed

### Frontend Issues
- Verify `VITE_API_URL` is set correctly
- Check browser console for API connection errors
- Ensure backend service is running and accessible

### WebSocket Issues
- Use `wss://` for secure WebSocket connections in production
- Check that WebSocket endpoint is accessible: `/ws/{pc_id}`

## Support

For issues or questions, check the repository: https://github.com/Jarvis4everyone/hackerrrr

