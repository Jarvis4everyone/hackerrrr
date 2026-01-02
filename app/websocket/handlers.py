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
from app.services.webrtc_service import webrtc_service
from app.services.file_service import FileService
from app.services.terminal_service import terminal_service
from app.websocket.terminal_handlers import forward_terminal_output
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
                
                # Update last_seen
                await PCService.update_last_seen(pc_id)
                
                # Handle different message types from client
                message_type = data.get("type")
                
                if message_type == "heartbeat":
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
                    logger.info(f"[{pc_id}] PC info updated: hostname={hostname}, name={pc_name}, ip={final_ip_address or 'not updated'}, saved IP in DB: {updated_pc.ip_address if updated_pc else 'N/A'}")
                
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
                    
                    if execution_id:
                        # Update execution status
                        execution = await ExecutionService.update_execution_status(
                            execution_id,
                            status,
                            error_message=error_message,
                            result=result
                        )
                        
                        # Store complete log content if provided in result
                        # PC clients now send complete log file content in execution_complete message
                        if execution and result and isinstance(result, dict):
                            log_content = result.get("log_content")
                            log_file_path = result.get("log_file")
                            
                            # Only store log if log_content is provided (new format)
                            # The complete log file content should be stored as a single log entry
                            if log_content:
                                try:
                                    # Check if log already exists for this execution
                                    existing_logs = await LogService.get_execution_logs(execution_id)
                                    
                                    # Only create log if it doesn't exist yet
                                    # (PC may send log in both "log" message and "execution_complete")
                                    if not existing_logs:
                                        log_entry = LogCreate(
                                            pc_id=pc_id,
                                            script_name=execution.script_name,
                                            execution_id=execution_id,
                                            log_file_path=log_file_path,
                                            log_content=log_content,  # Complete log file content (multiline)
                                            log_level="INFO"  # Default level, actual level may be in log content
                                        )
                                        await LogService.create_log(log_entry)
                                        logger.info(f"[{pc_id}] Complete log stored for execution {execution_id}: {execution.script_name}")
                                    else:
                                        logger.debug(f"[{pc_id}] Log already exists for execution {execution_id}, skipping duplicate")
                                except Exception as e:
                                    logger.error(f"Error storing log from execution_complete: {e}")
                
                elif message_type == "log":
                    # Receive complete log file content from PC
                    # PC clients now send the complete log file content as a single message after script execution
                    try:
                        execution_id = data.get("execution_id")
                        log_content = data.get("log_content", "")
                        
                        # Check if log already exists for this execution
                        # (PC may send log in both "log" message and "execution_complete")
                        if execution_id:
                            existing_logs = await LogService.get_execution_logs(execution_id)
                            if existing_logs:
                                logger.debug(f"[{pc_id}] Log already exists for execution {execution_id}, skipping duplicate")
                            else:
                                # Store complete log file content
                                log_entry = LogCreate(
                                    pc_id=pc_id,
                                    script_name=data.get("script_name", "unknown"),
                                    execution_id=execution_id,
                                    log_file_path=data.get("log_file_path"),
                                    log_content=log_content,  # Complete log file content (multiline string)
                                    log_level=data.get("log_level", "INFO")
                                )
                                await LogService.create_log(log_entry)
                                logger.info(f"[{pc_id}] Complete log file stored: {log_entry.script_name} (execution: {execution_id})")
                        else:
                            # Fallback: Store log even without execution_id (backward compatibility)
                            log_entry = LogCreate(
                                pc_id=pc_id,
                                script_name=data.get("script_name", "unknown"),
                                execution_id=execution_id,
                                log_file_path=data.get("log_file_path"),
                                log_content=log_content,
                                log_level=data.get("log_level", "INFO")
                            )
                            await LogService.create_log(log_entry)
                            logger.info(f"[{pc_id}] Log stored (no execution_id): {log_entry.script_name}")
                    except Exception as e:
                        logger.error(f"Error saving log from {pc_id}: {e}")
                
                # WebRTC Signaling Messages
                elif message_type == "webrtc_offer":
                    # PC sends offer, server creates answer
                    offer_sdp = data.get("sdp")
                    if offer_sdp:
                        # Define callback to send ICE candidates back to PC
                        async def send_ice_candidate_to_pc(pc_id: str, candidate):
                            """Send ICE candidate from server to PC client"""
                            try:
                                # Format candidate for sending
                                candidate_data = {
                                    "candidate": str(candidate.candidate) if hasattr(candidate, 'candidate') else str(candidate),
                                    "sdpMLineIndex": getattr(candidate, 'sdpMLineIndex', None),
                                    "sdpMid": getattr(candidate, 'sdpMid', None)
                                }
                                
                                await websocket.send_json({
                                    "type": "webrtc_ice_candidate",
                                    "candidate": candidate_data
                                })
                                logger.debug(f"[WebRTC] Sent ICE candidate to {pc_id}")
                            except Exception as e:
                                logger.error(f"[WebRTC] Error sending ICE candidate to {pc_id}: {e}")
                        
                        answer_sdp = await webrtc_service.handle_offer(pc_id, offer_sdp, send_ice_candidate_to_pc)
                        if answer_sdp:
                            await websocket.send_json({
                                "type": "webrtc_answer",
                                "sdp": answer_sdp
                            })
                            logger.info(f"[WebRTC] Sent answer to {pc_id}")
                        else:
                            await websocket.send_json({
                                "type": "webrtc_error",
                                "message": "Failed to create answer"
                            })
                
                elif message_type == "webrtc_answer":
                    # PC sends answer (for server-initiated connections)
                    answer_sdp = data.get("sdp")
                    if answer_sdp:
                        await webrtc_service.handle_answer(pc_id, answer_sdp)
                
                elif message_type == "webrtc_ice_candidate":
                    # PC sends ICE candidate
                    candidate = data.get("candidate")
                    if candidate:
                        await webrtc_service.handle_ice_candidate(pc_id, candidate)
                
                elif message_type == "webrtc_stream_ready":
                    # PC confirms stream is ready
                    stream_type = data.get("stream_type")
                    logger.info(f"[WebRTC] {pc_id} stream ready: {stream_type}")
                
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
                
                elif message_type == "terminal_error":
                    # PC reports terminal error
                    session_id = data.get("session_id")
                    error = data.get("error", "Unknown error")
                    logger.error(f"[Terminal] {pc_id} session {session_id} error: {error}")
                
                else:
                    logger.debug(f"[{pc_id}] Received message type: {message_type}")
                    
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except:
                    break
            
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
        await manager.disconnect(pc_id)

