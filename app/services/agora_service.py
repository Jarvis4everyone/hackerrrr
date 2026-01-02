"""
Agora Service for managing video/audio streaming
"""
import logging
import time
from typing import Optional, Dict
from app.config import settings

logger = logging.getLogger(__name__)

# Try to import Agora token builder
try:
    from agora_token_builder import RtcTokenBuilder, Role
    TOKEN_BUILDER_AVAILABLE = True
except ImportError:
    TOKEN_BUILDER_AVAILABLE = False
    logger.warning("agora-token-builder not installed. Using fallback token generation.")
    
    # Fallback Role enum
    class Role:
        PUBLISHER = 1
        SUBSCRIBER = 2
    
    # Fallback token builder
    class RtcTokenBuilder:
        @staticmethod
        def buildTokenWithUid(app_id, app_certificate, channel_name, uid, role, privilege_expired_ts):
            # Return temp token as fallback
            if settings.AGORA_TEMP_TOKEN:
                logger.warning(f"[Agora] Using fallback temp token (install agora-token-builder for proper token generation)")
                return settings.AGORA_TEMP_TOKEN
            raise ValueError("No token available - install agora-token-builder or set AGORA_TEMP_TOKEN")


class AgoraService:
    """Service for managing Agora connections"""
    
    def __init__(self):
        self.app_id = settings.AGORA_APP_ID
        self.app_certificate = settings.AGORA_APP_CERTIFICATE
        self.active_channels: Dict[str, str] = {}  # pc_id -> channel_name
        self.channel_tokens: Dict[str, str] = {}  # channel_name -> token
        
    def generate_token(self, channel_name: str, uid: int = 0, role: Role = Role.PUBLISHER, expire_time: int = 3600) -> str:
        """
        Generate Agora RTC token
        
        Args:
            channel_name: Channel name (typically PC ID)
            uid: User ID (0 for auto-assign)
            role: Role (PUBLISHER or SUBSCRIBER)
            expire_time: Token expiration time in seconds (default 1 hour)
        
        Returns:
            RTC token string
        """
        try:
            current_timestamp = int(time.time())
            privilege_expired_ts = current_timestamp + expire_time
            
            if TOKEN_BUILDER_AVAILABLE:
                token = RtcTokenBuilder.buildTokenWithUid(
                    self.app_id,
                    self.app_certificate,
                    channel_name,
                    uid,
                    role,
                    privilege_expired_ts
                )
                logger.info(f"[Agora] Generated token for channel '{channel_name}', uid={uid}, role={role.value if hasattr(role, 'value') else role}")
            else:
                # Use fallback
                token = RtcTokenBuilder.buildTokenWithUid(
                    self.app_id,
                    self.app_certificate,
                    channel_name,
                    uid,
                    role,
                    privilege_expired_ts
                )
                logger.warning(f"[Agora] Using fallback token for channel '{channel_name}'")
            
            return token
            
        except Exception as e:
            logger.error(f"[Agora] Error generating token: {e}", exc_info=True)
            # Return temp token as fallback if provided
            if settings.AGORA_TEMP_TOKEN:
                logger.warning(f"[Agora] Using fallback temp token due to error")
                return settings.AGORA_TEMP_TOKEN
            raise
    
    def start_stream(self, pc_id: str, stream_type: str) -> Dict[str, any]:
        """
        Start a stream for a PC
        
        Args:
            pc_id: PC identifier
            stream_type: Type of stream (camera, microphone, screen)
        
        Returns:
            Dictionary with channel_name, token, uid, and app_id
        """
        # Channel name format: {pc_id}_{stream_type}
        channel_name = f"{pc_id}_{stream_type}"
        
        # Store active channel
        self.active_channels[pc_id] = channel_name
        
        # Generate token for publisher (PC will publish)
        token = self.generate_token(channel_name, uid=0, role=Role.PUBLISHER)
        self.channel_tokens[channel_name] = token
        
        logger.info(f"[Agora] Started {stream_type} stream for PC '{pc_id}' on channel '{channel_name}'")
        
        return {
            "channel_name": channel_name,
            "token": token,
            "uid": 0,  # Auto-assign UID
            "app_id": self.app_id,
            "stream_type": stream_type
        }
    
    def get_subscriber_token(self, pc_id: str, stream_type: str, uid: int = 0) -> Dict[str, any]:
        """
        Get token for subscriber (frontend will subscribe)
        
        Args:
            pc_id: PC identifier
            stream_type: Type of stream (camera, microphone, screen)
            uid: User ID (0 for auto-assign)
        
        Returns:
            Dictionary with channel_name, token, uid, and app_id
        """
        channel_name = f"{pc_id}_{stream_type}"
        
        # Generate token for subscriber (frontend will subscribe)
        token = self.generate_token(channel_name, uid=uid, role=Role.SUBSCRIBER)
        
        logger.info(f"[Agora] Generated subscriber token for channel '{channel_name}', uid={uid}")
        
        return {
            "channel_name": channel_name,
            "token": token,
            "uid": uid,
            "app_id": self.app_id,
            "stream_type": stream_type
        }
    
    def stop_stream(self, pc_id: str) -> bool:
        """
        Stop stream for a PC
        
        Args:
            pc_id: PC identifier
        
        Returns:
            True if stream was stopped, False otherwise
        """
        if pc_id in self.active_channels:
            channel_name = self.active_channels.pop(pc_id)
            if channel_name in self.channel_tokens:
                del self.channel_tokens[channel_name]
            logger.info(f"[Agora] Stopped stream for PC '{pc_id}'")
            return True
        return False
    
    def has_active_stream(self, pc_id: str) -> bool:
        """Check if PC has an active stream"""
        return pc_id in self.active_channels
    
    def get_active_stream(self, pc_id: str) -> Optional[str]:
        """Get active stream type for a PC"""
        if pc_id in self.active_channels:
            channel_name = self.active_channels[pc_id]
            # Extract stream type from channel name: {pc_id}_{stream_type}
            parts = channel_name.split('_', 1)
            if len(parts) > 1:
                return parts[-1]  # Return stream_type
        return None


# Global Agora service instance
agora_service = AgoraService()

