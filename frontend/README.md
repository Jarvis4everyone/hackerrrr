# Remote Script Server - Frontend

A modern, responsive hacking-themed control panel for the Remote Script Server.

## Features

- 🎨 **Hacking Theme**: Dark, cyberpunk-style UI with green terminal aesthetics
- 📱 **Fully Responsive**: Works on desktop, tablet, and mobile devices
- 🖥️ **Dashboard**: Real-time statistics and system status
- 💻 **PC Management**: View and manage connected PCs
- 📜 **Scripts**: Send scripts to individual PCs or broadcast to all
- 📹 **Camera Streaming**: WebRTC camera feed from PCs
- 🎤 **Microphone Streaming**: Audio streaming with 5-second chunks
- 🖼️ **Screen Share**: Remote desktop viewing via WebRTC
- 📊 **Logs**: Execution history and filtering

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Build

```bash
npm run build
```

## Configuration

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
```

## Pages

- **Dashboard** (`/`): Overview with statistics
- **PCs** (`/pcs`): Manage connected PCs
- **Scripts** (`/scripts`): Send and manage scripts
- **Camera** (`/camera`): View camera streams
- **Microphone** (`/microphone`): Listen to microphone streams
- **Screen** (`/screen`): View screen shares
- **Logs** (`/logs`): Execution history

## Tech Stack

- React 18
- Vite
- Tailwind CSS
- React Router
- Axios
- Lucide React Icons

