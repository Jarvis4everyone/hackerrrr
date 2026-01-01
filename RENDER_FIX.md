# Fix for Render Dockerfile Error

## The Problem
Render is looking for `Dockerfile` (default name) but we have `Dockerfile.backend` and `Dockerfile.frontend`.

## Solutions

### Option 1: Use Blueprint (Recommended)
1. Go to Render Dashboard → **New** → **Blueprint**
2. Connect your GitHub repo
3. Render will use `render.yaml` which specifies the correct Dockerfile paths

### Option 2: Manual Service Creation
When creating services manually, you MUST specify the Dockerfile path:

**For Backend:**
- Environment: Docker
- **Dockerfile Path**: `Dockerfile.backend` (NOT `./Dockerfile.backend`)
- Docker Context: `.`

**For Frontend:**
- Environment: Docker  
- **Dockerfile Path**: `Dockerfile.frontend` (NOT `./Dockerfile.frontend`)
- Docker Context: `.`

### Option 3: Rename Files (If auto-detection is needed)
If Render auto-detects, it looks for `Dockerfile`. You could:
- Create a default `Dockerfile` that copies the appropriate one
- Or use symlinks (not recommended for Windows/Git)

## Important Notes
- The `dockerfilePath` in `render.yaml` should be `Dockerfile.backend` (without `./`)
- Make sure you're using **Blueprint** mode, not manual service creation
- If using manual creation, explicitly set the Dockerfile path in the UI

