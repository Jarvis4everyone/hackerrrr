"""
WebSocket Handlers for Frontend Streaming Connections
"""
import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect
from app.websocket.connection_manager import manager
from app.services.streaming_service import streaming_service

logger = logging.getLogger(__name__)


async def handle_frontend_stream(websocket: WebSocket, pc_id: str, stream_type: str):
    """
    Handle frontend WebSocket connection for receiving streams
    
    Args:
        websocket: Frontend WebSocket connection
        pc_id: PC ID to receive stream from
        stream_type: Type of stream ('camera', 'microphone', 'screen')
    """
    try:
        await websocket.accept()
        logger.info(f"[Streaming] Frontend connected for {pc_id} - {stream_type}")
        
        # Add frontend connection to streaming service
        await streaming_service.add_frontend_connection(pc_id, stream_type, websocket)
        
        # Send initial status
        is_streaming = await streaming_service.get_pc_streaming_status(pc_id, stream_type)
        await websocket.send_json({
            "type": "stream_status",
            "stream_type": stream_type,
            "status": "connected",
            "pc_streaming": is_streaming
        })
        
        # Keep connection alive and listen for messages
        while True:
            try:
                # Wait for messages from frontend (control messages, etc.)
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                
                message_type = data.get("type")
                
                if message_type == "start_stream":
                    # Frontend requests to start stream
                    # Forward request to PC client
                    pc_websocket = manager.get_connection(pc_id)
                    if pc_websocket:
                        try:
                            await pc_websocket.send_json({
                                "type": "start_stream",
                                "stream_type": stream_type
                            })
                            logger.info(f"[Streaming] Start {stream_type} requested for {pc_id}")
                            await websocket.send_json({
                                "type": "stream_status",
                                "stream_type": stream_type,
                                "status": "starting"
                            })
                        except Exception as e:
                            logger.error(f"[Streaming] Error sending start command: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Failed to send start command to PC: {str(e)}"
                            })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"PC {pc_id} is not connected"
                        })
                
                elif message_type == "stop_stream":
                    # Frontend requests to stop stream
                    # Forward request to PC client
                    pc_websocket = manager.get_connection(pc_id)
                    if pc_websocket:
                        try:
                            await pc_websocket.send_json({
                                "type": "stop_stream",
                                "stream_type": stream_type
                            })
                            logger.info(f"[Streaming] Stop {stream_type} requested for {pc_id}")
                            # Update status
                            await streaming_service.set_pc_streaming_status(pc_id, stream_type, False)
                        except Exception as e:
                            logger.error(f"[Streaming] Error sending stop command: {e}")
                            # Still update status even if send fails
                            await streaming_service.set_pc_streaming_status(pc_id, stream_type, False)
                
                elif message_type == "ping":
                    # Heartbeat
                    await websocket.send_json({"type": "pong"})
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except:
                    break
            
            except WebSocketDisconnect:
                break
            
            except Exception as e:
                logger.error(f"[Streaming] Error in frontend stream handler for {pc_id}/{stream_type}: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[Streaming] WebSocket error for frontend stream {pc_id}/{stream_type}: {e}")
    finally:
        # Remove frontend connection
        await streaming_service.remove_frontend_connection(pc_id, stream_type, websocket)
        logger.info(f"[Streaming] Frontend disconnected for {pc_id} - {stream_type}")

