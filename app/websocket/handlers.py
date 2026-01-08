"""
WebSocket Handlers
"""
import asyncio
import base64
from fastapi import WebSocket, WebSocketDisconnect
from app.websocket.connection_manager import manager
from app.services.pc_service import PCService
from app.services.execution_service import ExecutionService
from app.services.log_service import LogService
from app.services.file_service import FileService
from app.services.terminal_service import terminal_service
from app.websocket.terminal_handlers import forward_terminal_output
from app.services.streaming_service import streaming_service
from app.models.log import LogCreate
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def handle_websocket_connection(websocket: WebSocket, pc_id: str):
    """Handle WebSocket connection for a PC"""
    pc_name = None
    hostname = None
    
    # Extract IP address from WebSocket connection
    ip_address = None
    try:
        if websocket.client:
            ip_address = websocket.client.host
    except Exception as e:
        logger.warning(f"Could not extract IP address for {pc_id}: {e}")
    
    try:
        # Accept connection with IP address
        await manager.connect(websocket, pc_id, pc_name, ip_address=ip_address, hostname=hostname)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": f"Connected to server as {pc_id}",
            "server_url": f"http://{settings.HOST}:{settings.PORT}"
        })
        
        # Keep connection alive and listen for messages
        while True:
            try:
                # Wait for messages from client (heartbeat, status updates, etc.)
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=settings.WS_HEARTBEAT_TIMEOUT
                )
                
                # Update last_seen and ensure connected status is true
                # Any message from PC means it's connected
                await PCService.update_connection_status(pc_id, connected=True)
                
                # Handle different message types from client
                message_type = data.get("type")
                
                if message_type == "heartbeat":
                    # Heartbeat received - PC is definitely connected
                    await PCService.update_connection_status(pc_id, connected=True)
                    await websocket.send_json({"type": "heartbeat", "status": "ok"})
                
                elif message_type == "status":
                    logger.info(f"[{pc_id}] Status: {data.get('message', 'No message')}")
                
                elif message_type == "pc_info":
                    # PC sends hostname, IP address, and other info
                    # Prioritize IP address from PC client over WebSocket connection IP
                    # Check both top-level and metadata for IP address
                    pc_ip_address = data.get("ip_address")
                    metadata = data.get("metadata", {})
                    
                    # If IP not at top level, check metadata
                    if not pc_ip_address and isinstance(metadata, dict):
                        pc_ip_address = metadata.get("ip_address")
                        logger.debug(f"[{pc_id}] Found IP in metadata: {pc_ip_address}")
                    
                    hostname = data.get("hostname")
                    pc_name = data.get("name")
                    os_info = data.get("os_info")
                    
                    # Use PC-provided IP if available, otherwise don't update IP (preserve existing)
                    # Only pass ip_address if PC explicitly provided it
                    final_ip_address = pc_ip_address if pc_ip_address else None
                    
                    logger.info(f"[{pc_id}] Processing pc_info - received IP: {pc_ip_address}, final IP: {final_ip_address}, metadata keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'N/A'}")
                    
                    # Remove ip_address from metadata if it was there (to avoid duplication)
                    if isinstance(metadata, dict) and "ip_address" in metadata:
                        metadata = {k: v for k, v in metadata.items() if k != "ip_address"}
                    
                    # CRITICAL: Ensure WebSocket connection is registered in manager
                    # If pc_info is received but connection is not in manager, add it
                    if not manager.is_connected(pc_id):
                        logger.warning(f"[{pc_id}] Received pc_info but WebSocket not in active_connections - registering connection")
                        # Re-register the connection
                        manager.active_connections[pc_id] = websocket
                    
                    # CRITICAL: Ensure connected status is true when receiving pc_info
                    # This ensures PC is marked as online even if connection handler missed it
                    await PCService.update_connection_status(pc_id, connected=True)
                    
                    # Update PC with hostname, IP address, and other info
                    # Always update when pc_info is received (even if some fields are None)
                    updated_pc = await PCService.create_or_update_pc(
                        pc_id=pc_id,
                        name=pc_name,
                        ip_address=final_ip_address,  # Will only update if not None
                        hostname=hostname,
                        os_info=os_info,
                        metadata=metadata
                    )
                    
                    # Ensure connected is still true after update
                    await PCService.update_connection_status(pc_id, connected=True)
                    logger.info(f"[{pc_id}] PC info updated: hostname={hostname}, name={pc_name}, ip={final_ip_address or 'not updated'}, saved IP in DB: {updated_pc.ip_address if updated_pc else 'N/A'}, connected: {updated_pc.connected if updated_pc else 'N/A'}")
                
                elif message_type == "error":
                    error_msg = data.get('message', 'Unknown error')
                    logger.error(f"[{pc_id}] Error: {error_msg}")
                    
                    # Update execution if execution_id is provided
                    execution_id = data.get("execution_id")
                    if execution_id:
                        await ExecutionService.update_execution_status(
                            execution_id,
                            "failed",
                            error_message=error_msg
                        )
                
                elif message_type == "result":
                    result_msg = data.get('message', 'No result')
                    logger.info(f"[{pc_id}] Result: {result_msg}")
                    
                    # Update execution if execution_id is provided
                    execution_id = data.get("execution_id")
                    if execution_id:
                        await ExecutionService.update_execution_status(
                            execution_id,
                            "success",
                            result={"message": result_msg, "data": data.get("data")}
                        )
                
                elif message_type == "execution_complete":
                    execution_id = data.get("execution_id")
                    status = data.get("status", "success")
                    error_message = data.get("error_message")
                    result = data.get("result")
                    
                    logger.info(f"[{pc_id}] Received execution_complete - execution_id: {execution_id}, status: {status}")
                    
                    if execution_id:
                        # Update execution status
                        execution = await ExecutionService.update_execution_status(
                            execution_id,
                            status,
                            error_message=error_message,
                            result=result
                        )
                        
                        logger.info(f"[{pc_id}] Execution status updated - execution_id: {execution_id}, status: {status}")
                        
                        # Store complete log content if provided in result
                        # PC clients may send complete log file content in execution_complete message
                        if execution and result and isinstance(result, dict):
                            log_content = result.get("log_content")
                            log_file_path = result.get("log_file")
                            
                            # Store log if log_content is provided
                            # Note: PC may have already sent this via "log" message, but we store it anyway
                            # to ensure we have the complete log file
                            if log_content:
                                try:
                                        log_entry = LogCreate(
                                            pc_id=pc_id,
                                            script_name=execution.script_name,
                                            execution_id=execution_id,
                                            log_file_path=log_file_path,
                                        log_content=log_content,
                                        log_level="SUCCESS" if status == "success" else "ERROR"
                                    )
                                    stored_log = await LogService.create_log(log_entry)
                                    logger.info(f"[{pc_id}] Complete log stored from execution_complete - ID: {stored_log.id}, execution: {execution_id}")
                                except Exception as e:
                                    logger.error(f"[{pc_id}] Error storing log from execution_complete: {e}", exc_info=True)
                    else:
                        logger.warning(f"[{pc_id}] Received execution_complete without execution_id")
                
                elif message_type == "log":
                    # Receive log messages from PC client
                    # According to PC client documentation, the PC sends ONE log message per execution_id
                    # containing the COMPLETE log file content as a single string.
                    #
                    # CRITICAL: LogService.create_log() will:
                    # - If log exists for execution_id: UPDATE it (replace content, not append)
                    # - If log doesn't exist: CREATE new document
                    # This ensures ONE document per execution_id with complete log content.
                    try:
                        execution_id = data.get("execution_id")
                        script_name = data.get("script_name", "unknown")
                        log_content = data.get("log_content", "")
                        log_level = data.get("log_level", "INFO")
                        log_file_path = data.get("log_file_path")
                        
                        # CRITICAL: Log every received message for debugging
                        logger.info(f"[{pc_id}] 📥 LOG MESSAGE RECEIVED - script: {script_name}, execution_id: {execution_id}, level: {log_level}, content_length: {len(log_content) if log_content else 0}")
                        
                        # Validate required fields
                        if not execution_id:
                            logger.error(f"[{pc_id}] ❌ Log message missing execution_id - cannot save")
                        elif not log_content:
                            logger.warning(f"[{pc_id}] ⚠️ Log message has empty content - script: {script_name}, execution_id: {execution_id}")
                        else:
                            # Create log entry - LogService will handle update vs create
                            log_entry = LogCreate(
                                pc_id=pc_id,  # From WebSocket connection, NOT from message
                                script_name=script_name,
                                execution_id=execution_id,
                                log_file_path=log_file_path,
                                log_content=log_content,  # Complete log file content (can be 8000+ chars)
                                log_level=log_level
                            )
                            
                            # Save to MongoDB - this will update existing or create new
                            stored_log = await LogService.create_log(log_entry)
                            logger.info(f"[{pc_id}] ✅ LOG SAVED TO MONGODB - ID: {stored_log.id}, script: {script_name}, execution: {execution_id}, level: {log_level}, content_length: {len(log_content)}, saved_length: {len(stored_log.log_content)}")
                            
                    except Exception as e:
                        logger.error(f"[{pc_id}] ❌ CRITICAL ERROR saving log message: {e}", exc_info=True)
                        logger.error(f"[{pc_id}] Failed log data: script_name={data.get('script_name')}, execution_id={data.get('execution_id')}, log_level={data.get('log_level')}, content_length={len(data.get('log_content', ''))}")
                        # Don't break the connection on log errors - continue processing other messages
                
                elif message_type == "file_download_response":
                    # PC sends file download response
                    request_id = data.get("request_id")
                    file_path = data.get("file_path")
                    success = data.get("success", False)
                    error_message = data.get("error_message")
                    
                    if success:
                        # File content is base64 encoded
                        file_content_b64 = data.get("file_content")
                        if file_content_b64:
                            try:
                                # Decode base64 content
                                file_content = base64.b64decode(file_content_b64)
                                
                                # Save file
                                file_info = await FileService.save_file(
                                    pc_id=pc_id,
                                    file_path=file_path,
                                    file_content=file_content
                                )
                                
                                logger.info(f"[{pc_id}] File downloaded successfully: {file_path} ({file_info['size_mb']} MB)")
                                
                                # Send confirmation to PC
                                await websocket.send_json({
                                    "type": "file_download_complete",
                                    "request_id": request_id,
                                    "success": True,
                                    "file_id": file_info["file_id"]
                                })
                            except ValueError as e:
                                # File too large
                                logger.error(f"[{pc_id}] File download failed: {e}")
                                await websocket.send_json({
                                    "type": "file_download_complete",
                                    "request_id": request_id,
                                    "success": False,
                                    "error_message": str(e)
                                })
                            except Exception as e:
                                logger.error(f"[{pc_id}] Error saving file: {e}")
                                await websocket.send_json({
                                    "type": "file_download_complete",
                                    "request_id": request_id,
                                    "success": False,
                                    "error_message": f"Server error: {str(e)}"
                                })
                        else:
                            logger.error(f"[{pc_id}] File download response missing file_content")
                            await websocket.send_json({
                                "type": "file_download_complete",
                                "request_id": request_id,
                                "success": False,
                                "error_message": "File content missing"
                            })
                    else:
                        # Download failed on PC side
                        logger.error(f"[{pc_id}] File download failed: {error_message}")
                        await websocket.send_json({
                            "type": "file_download_complete",
                            "request_id": request_id,
                            "success": False,
                            "error_message": error_message
                        })
                
                elif message_type == "terminal_output":
                    # PC sends terminal output
                    session_id = data.get("session_id")
                    output = data.get("output", "")
                    is_complete = data.get("is_complete", False)
                    
                    if session_id and terminal_service.is_session_active(session_id):
                        # Forward output to frontend
                        await forward_terminal_output(pc_id, session_id, output, is_complete)
                        logger.debug(f"[Terminal] {pc_id} session {session_id}: {len(output)} chars")
                    else:
                        logger.warning(f"[Terminal] Received output for inactive session: {session_id}")
                
                elif message_type == "terminal_ready":
                    # PC confirms terminal session is ready
                    session_id = data.get("session_id")
                    if session_id:
                        logger.info(f"[Terminal] {pc_id} terminal session ready: {session_id}")
                        # Forward ready notification to frontend
                        from app.websocket.terminal_handlers import forward_terminal_ready
                        await forward_terminal_ready(pc_id, session_id)
                
                elif message_type == "terminal_error":
                    # PC reports terminal error
                    session_id = data.get("session_id")
                    error = data.get("error", "Unknown error")
                    logger.error(f"[Terminal] {pc_id} session {session_id} error: {error}")
                    # Forward error to frontend
                    if session_id:
                        from app.websocket.terminal_handlers import forward_terminal_error
                        await forward_terminal_error(pc_id, session_id, error)
                
                elif message_type == "camera_frame":
                    # PC sends camera frame (base64 encoded JPEG)
                    # Update last_seen - streaming activity means PC is online
                    await PCService.update_last_seen(pc_id)
                    
                    frame_data = data.get("frame")
                    if frame_data:
                        try:
                            # Forward to all frontend connections
                            await streaming_service.broadcast_to_frontend(
                                pc_id, 
                                "camera", 
                                {"type": "camera_frame", "frame": frame_data}
                            )
                        except Exception as e:
                            logger.error(f"[Streaming] Error broadcasting camera frame: {e}")
                
                elif message_type == "microphone_audio":
                    # PC sends microphone audio chunk (base64 encoded)
                    # Update last_seen - streaming activity means PC is online
                    await PCService.update_last_seen(pc_id)
                    
                    audio_data = data.get("audio")
                    if audio_data:
                        try:
                            # Forward to all frontend connections
                            await streaming_service.broadcast_to_frontend(
                                pc_id,
                                "microphone",
                                {"type": "microphone_audio", "audio": audio_data}
                            )
                        except Exception as e:
                            logger.error(f"[Streaming] Error broadcasting microphone audio: {e}")
                
                elif message_type == "screen_frame":
                    # PC sends screen frame (base64 encoded JPEG)
                    # Update last_seen - streaming activity means PC is online
                    await PCService.update_last_seen(pc_id)
                    
                    frame_data = data.get("frame")
                    if frame_data:
                        try:
                            # Forward to all frontend connections
                            await streaming_service.broadcast_to_frontend(
                                pc_id,
                                "screen",
                                {"type": "screen_frame", "frame": frame_data}
                            )
                        except Exception as e:
                            logger.error(f"[Streaming] Error broadcasting screen frame: {e}")
                
                elif message_type == "stream_status":
                    # PC reports streaming status
                    stream_type = data.get("stream_type")  # 'camera', 'microphone', 'screen'
                    status = data.get("status")  # 'started', 'stopped', 'error'
                    error = data.get("error")
                    
                    if stream_type:
                        is_streaming = status == "started"
                        await streaming_service.set_pc_streaming_status(pc_id, stream_type, is_streaming)
                        
                        if status == "error":
                            logger.error(f"[Streaming] {pc_id} {stream_type} error: {error}")
                        else:
                            logger.info(f"[Streaming] {pc_id} {stream_type}: {status}")
                
                else:
                    logger.debug(f"[{pc_id}] Received message type: {message_type}")
                    
            except asyncio.TimeoutError:
                # Timeout waiting for message - this is normal when PC is busy
                # Don't close connection - just continue waiting
                # The PC will send heartbeat or other messages when ready
                # Update last_seen to keep connection alive if WebSocket is still active
                if manager.is_connected(pc_id):
                    await PCService.update_last_seen(pc_id)
                continue
            
            except WebSocketDisconnect:
                break
            
            except Exception as e:
                logger.error(f"Error handling message from {pc_id}: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for {pc_id}: {e}")
    finally:
        # Clean up streaming connections when PC disconnects
        await streaming_service.cleanup_pc_connections(pc_id)
        await manager.disconnect(pc_id)

