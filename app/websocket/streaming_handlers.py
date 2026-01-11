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
        # Check if PC is actually connected before sending status
        is_connected = await manager.ensure_connection_synced(pc_id)
        is_streaming = await streaming_service.get_pc_streaming_status(pc_id, stream_type)
        await websocket.send_json({
            "type": "stream_status",
            "stream_type": stream_type,
            "status": "connected" if is_connected else "pc_offline",
            "pc_streaming": is_streaming,
            "pc_connected": is_connected
        })
        
        if not is_connected:
            logger.warning(f"[Streaming] Frontend connected for {pc_id} - {stream_type}, but PC is not connected")
        
        # Keep connection alive and listen for messages
        while True:
            try:
                # Wait for messages from frontend (control messages, etc.)
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                
                message_type = data.get("type")
                
                if message_type == "start_stream":
                    # Frontend requests to start stream
                    # Forward request to PC client
                    # Use ensure_connection_synced to check if PC is actually connected
                    is_connected = await manager.ensure_connection_synced(pc_id)
                    if is_connected:
                        pc_websocket = manager.get_connection(pc_id)
                        if pc_websocket:
                            try:
                                # Use send_personal_message for proper error handling
                                success = await manager.send_personal_message({
                                    "type": "start_stream",
                                    "stream_type": stream_type
                                }, pc_id)
                                if success:
                                    logger.info(f"[Streaming] Start {stream_type} requested for {pc_id}")
                                    await websocket.send_json({
                                        "type": "stream_status",
                                        "stream_type": stream_type,
                                        "status": "starting"
                                    })
                                else:
                                    logger.warning(f"[Streaming] Failed to send start command to {pc_id} - connection may have closed")
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": f"PC {pc_id} connection lost"
                                    })
                            except Exception as e:
                                logger.error(f"[Streaming] Error sending start command: {e}")
                                await websocket.send_json({
                                    "type": "error",
                                    "message": f"Failed to send start command to PC: {str(e)}"
                                })
                        else:
                            # Connection exists in DB but not in active_connections - might be syncing
                            logger.warning(f"[Streaming] PC {pc_id} marked as connected but WebSocket not found - may be syncing")
                            await websocket.send_json({
                                "type": "error",
                                "message": f"PC {pc_id} connection is syncing, please try again"
                            })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"PC {pc_id} is not connected"
                        })
                
                elif message_type == "stop_stream":
                    # Frontend requests to stop stream
                    # Forward request to PC client
                    is_connected = await manager.ensure_connection_synced(pc_id)
                    if is_connected:
                        pc_websocket = manager.get_connection(pc_id)
                        if pc_websocket:
                            try:
                                # Use send_personal_message for proper error handling
                                success = await manager.send_personal_message({
                                    "type": "stop_stream",
                                    "stream_type": stream_type
                                }, pc_id)
                                if success:
                                    logger.info(f"[Streaming] Stop {stream_type} requested for {pc_id}")
                                # Update status regardless of send success
                                await streaming_service.set_pc_streaming_status(pc_id, stream_type, False)
                            except Exception as e:
                                logger.error(f"[Streaming] Error sending stop command: {e}")
                                # Still update status even if send fails
                                await streaming_service.set_pc_streaming_status(pc_id, stream_type, False)
                        else:
                            # Connection exists in DB but not in active_connections
                            # Still update status to stop
                            await streaming_service.set_pc_streaming_status(pc_id, stream_type, False)
                    else:
                        # PC not connected, but still update status to stop
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

