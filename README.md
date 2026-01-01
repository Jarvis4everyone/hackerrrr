# Remote Script Server

A FastAPI-based WebSocket server with MongoDB for managing multiple PC connections and remotely executing scripts.

## Features

- **WebSocket Communication**: Fast, real-time communication with connected PCs
- **MongoDB Integration**: All data stored in MongoDB (PCs, scripts, executions)
- **Multiple PC Management**: Track and manage multiple connected PCs simultaneously
- **Script Distribution**: Send Python scripts from the `Scripts/` folder to any connected PC
- **Execution Tracking**: Track all script executions with status, results, and error messages
- **Connection Tracking**: Monitor connected PCs with metadata (name, connection time, last seen)
- **Broadcast Support**: Send scripts to all connected PCs at once
- **RESTful API**: Clean API structure with proper routes and services

## Project Structure

```
SERVER/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── database.py          # MongoDB connection
│   ├── models/              # Pydantic models and schemas
│   │   ├── pc.py
│   │   ├── script.py
│   │   ├── execution.py
│   │   └── request.py
│   ├── routes/              # API routes
│   │   ├── pcs.py
│   │   ├── scripts.py
│   │   ├── executions.py
│   │   └── health.py
│   ├── services/            # Business logic
│   │   ├── pc_service.py
│   │   ├── script_service.py
│   │   └── execution_service.py
│   └── websocket/           # WebSocket handlers
│       ├── connection_manager.py
│       └── handlers.py
├── Scripts/                 # Python scripts to be sent to PCs
├── requirements.txt
├── .env.example
├── run.py                   # Server runner
└── README.md
```

## Installation

1. **Install MongoDB** (if not already installed):
   - Download from [MongoDB Download Center](https://www.mongodb.com/try/download/community)
   - Or use Docker: `docker run -d -p 27017:27017 --name mongodb mongo`

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your settings
```

## Configuration

Create a `.env` file with the following variables:

```env
# Server Configuration
HOST=0.0.0.0
PORT=5000
DEBUG=True

# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=remote_script_server
```

## Running the Server

```bash
python run.py
```

Or:

```bash
python -m app.main
```

The server will start on `http://localhost:5000` by default.

## Running the Frontend

The frontend is a React application located in the `frontend/` directory.

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`

For production build:

```bash
cd frontend
npm run build
```

## API Endpoints

### WebSocket Connection
- **Endpoint**: `ws://localhost:5000/ws/{pc_id}`
- **Description**: Connect a PC to the server using WebSocket
- **Example**: `ws://localhost:5000/ws/PC-001`

### REST API Endpoints

#### Health & Info
- **GET** `/` - Root endpoint with API information
- **GET** `/api/health` - Health check endpoint

#### PCs Management
- **GET** `/api/pcs` - List all PCs (query param: `connected_only=true` to filter)
- **GET** `/api/pcs/{pc_id}` - Get specific PC details
- **GET** `/api/pcs/{pc_id}/connected` - Check if PC is connected
- **DELETE** `/api/pcs/{pc_id}` - Delete a PC record

#### Scripts Management
- **GET** `/api/scripts` - List all available scripts
- **GET** `/api/scripts/sync` - Sync scripts from file system to database
- **POST** `/api/scripts/send` - Send script to a specific PC
- **POST** `/api/scripts/broadcast` - Broadcast script to all connected PCs

#### Executions Tracking
- **GET** `/api/executions` - Get recent executions (query param: `limit`)
- **GET** `/api/executions/{execution_id}` - Get specific execution details
- **GET** `/api/executions/pc/{pc_id}` - Get executions for a PC
- **GET** `/api/executions/script/{script_name}` - Get executions for a script

## Usage Examples

### Using curl

**List connected PCs:**
```bash
curl http://localhost:5000/api/pcs
```

**Send a script to a specific PC:**
```bash
curl -X POST "http://localhost:5000/api/scripts/send?pc_id=PC-001&script_name=screenshot.py"
```

**Send a script (using JSON body):**
```bash
curl -X POST "http://localhost:5000/api/scripts/send" \
  -H "Content-Type: application/json" \
  -d '{"pc_id": "PC-001", "script_name": "screenshot.py", "server_url": "http://localhost:5000"}'
```

**Broadcast a script to all PCs:**
```bash
curl -X POST "http://localhost:5000/api/scripts/broadcast?script_name=lock_pc.py"
```

**Get execution history:**
```bash
curl http://localhost:5000/api/executions?limit=50
```

### Using Python requests

```python
import requests

# List connected PCs
response = requests.get("http://localhost:5000/api/pcs")
print(response.json())

# Send script to PC
response = requests.post(
    "http://localhost:5000/api/scripts/send",
    json={
        "pc_id": "PC-001",
        "script_name": "screenshot.py",
        "server_url": "http://localhost:5000"
    }
)
print(response.json())

# Get execution history for a PC
response = requests.get("http://localhost:5000/api/executions/pc/PC-001")
print(response.json())
```

## MongoDB Collections

The server uses the following MongoDB collections:

- **`pcs`**: PC information and connection status
- **`scripts`**: Script metadata and content
- **`executions`**: Script execution history with status and results

## Message Format

### Server to Client (Script Message)
```json
{
    "type": "script",
    "script_name": "screenshot.py",
    "script_content": "# Python script content...",
    "server_url": "http://localhost:5000",
    "execution_id": "507f1f77bcf86cd799439011"
}
```

### Client to Server (Status Messages)
```json
{
    "type": "heartbeat",
    "status": "ok"
}
```

```json
{
    "type": "execution_complete",
    "execution_id": "507f1f77bcf86cd799439011",
    "status": "success",
    "result": {"message": "Script executed successfully"}
}
```

## Client Implementation

The client PC should:
1. Connect to the WebSocket endpoint: `ws://localhost:5000/ws/{pc_id}`
2. Listen for messages with `type: "script"`
3. Execute the received script content
4. Send execution status back to the server using `execution_complete` message type

See `example_client.py` for a reference implementation.

## Development

The codebase follows a clean architecture pattern:

- **Models**: Pydantic models for data validation
- **Routes**: FastAPI route handlers
- **Services**: Business logic separated from routes
- **WebSocket**: Separate handlers for WebSocket connections
- **Database**: MongoDB with Motor (async driver)

## Notes

- The server automatically handles disconnections
- Scripts are read from the `Scripts/` directory
- All scripts must be Python files (`.py` extension)
- The server URL can be injected into scripts that require it
- All executions are tracked in MongoDB with status and results
- Scripts are synced to MongoDB on server startup
