"""
WebSocket Handlers for Frontend Terminal Sessions
"""
import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect
from app.websocket.connection_manager import manager
from app.services.terminal_service import terminal_service

logger = logging.getLogger(__name__)


async def handle_frontend_terminal(websocket: WebSocket, pc_id: str, session_id: str):
    """Handle frontend terminal WebSocket connection"""
    try:
        await websocket.accept()
        logger.info(f"[Frontend Terminal] Frontend connected for {pc_id} session {session_id}")
        
        # Verify session is active (but don't close if not - PC might be starting)
        if not terminal_service.is_session_active(session_id):
            logger.warning(f"[Frontend Terminal] Session {session_id} not active yet, but allowing connection")
            # Don't close - allow connection and wait for session to become active
            # The PC might be starting the terminal process
        
        # Store frontend connection for this session
        frontend_terminal_connections[session_id] = websocket
        logger.info(f"[Frontend Terminal] Frontend connection stored for session {session_id}")
        
        # Listen for messages from frontend
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                message_type = data.get("type")
                
                if message_type == "command":
                    # Frontend sends a command
                    command = data.get("command", "")
                    if command:
                        # Send command to PC
                        await manager.send_terminal_command(pc_id, session_id, command)
                        logger.debug(f"[Frontend Terminal] Command sent: {command[:50]}")
                
                elif message_type == "interrupt":
                    # Frontend sends Ctrl+C interrupt
                    await manager.send_terminal_interrupt(pc_id, session_id)
                    logger.debug(f"[Frontend Terminal] Interrupt sent for session {session_id}")
                
                elif message_type == "ping":
                    # Heartbeat
                    await websocket.send_json({"type": "pong"})
                
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_json({"type": "ping"})
                except:
                    break
            
            except WebSocketDisconnect:
                break
            
            except Exception as e:
                logger.error(f"[Frontend Terminal] Error handling message: {e}")
                break
        
        # Cleanup
        if session_id in frontend_terminal_connections:
            del frontend_terminal_connections[session_id]
        
        logger.info(f"[Frontend Terminal] Frontend disconnected for {pc_id} session {session_id}")
        
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[Frontend Terminal] Error: {e}")


# Store frontend connections globally
frontend_terminal_connections = {}


async def forward_terminal_output(pc_id: str, session_id: str, output: str, is_complete: bool = False):
    """
    Forward terminal output from PC to frontend - optimized for batch output
    
    Args:
        pc_id: PC ID
        session_id: Session ID
        output: Terminal output (can be large batch of output)
        is_complete: Whether the command is complete
    """
    if session_id in frontend_terminal_connections:
        websocket = frontend_terminal_connections[session_id]
        try:
            # Send immediately without any delays - use send_json for efficiency
            # FastAPI's send_json is already optimized, no need for additional buffering
            await websocket.send_json({
                "type": "output",
                "output": output,
                "is_complete": is_complete
            })
            logger.debug(f"[Frontend Terminal] Successfully sent output to frontend for session {session_id}: {len(output)} chars")
        except Exception as e:
            logger.error(f"[Frontend Terminal] Error forwarding output: {e}", exc_info=True)
            # Remove dead connection
            if session_id in frontend_terminal_connections:
                del frontend_terminal_connections[session_id]
    else:
        logger.warning(f"[Frontend Terminal] No frontend connection for session {session_id}, output not forwarded. Available sessions: {list(frontend_terminal_connections.keys())}")


async def forward_terminal_error(pc_id: str, session_id: str, error: str):
    """
    Forward terminal error from PC to frontend
    
    Args:
        pc_id: PC ID
        session_id: Session ID
        error: Error message
    """
    if session_id in frontend_terminal_connections:
        websocket = frontend_terminal_connections[session_id]
        try:
            await websocket.send_json({
                "type": "error",
                "message": error
            })
        except Exception as e:
            logger.error(f"[Frontend Terminal] Error forwarding error message: {e}")
            if session_id in frontend_terminal_connections:
                del frontend_terminal_connections[session_id]
    else:
        logger.debug(f"[Frontend Terminal] No frontend connection for session {session_id}, error not forwarded")


async def forward_terminal_ready(pc_id: str, session_id: str):
    """
    Forward terminal ready notification from PC to frontend
    
    Args:
        pc_id: PC ID
        session_id: Session ID
    """
    if session_id in frontend_terminal_connections:
        websocket = frontend_terminal_connections[session_id]
        try:
            await websocket.send_json({
                "type": "ready",
                "message": "Terminal session is ready"
            })
        except Exception as e:
            logger.error(f"[Frontend Terminal] Error forwarding ready message: {e}")
            if session_id in frontend_terminal_connections:
                del frontend_terminal_connections[session_id]
    else:
        logger.debug(f"[Frontend Terminal] No frontend connection for session {session_id}, ready message not forwarded")

