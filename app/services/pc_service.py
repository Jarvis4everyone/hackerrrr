"""
PC Service - Business logic for PC management
"""
from typing import List, Optional
from datetime import datetime
from app.database import get_database
from app.models.pc import PC, PCInDB
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


class PCService:
    """Service for managing PCs"""
    
    @staticmethod
    async def get_pc(pc_id: str) -> Optional[PCInDB]:
        """Get a PC by ID"""
        db = get_database()
        pc_data = await db.pcs.find_one({"pc_id": pc_id})
        if pc_data:
            pc_data["_id"] = str(pc_data["_id"])
            return PCInDB(**pc_data)
        return None
    
    @staticmethod
    async def get_all_pcs(connected_only: bool = False) -> List[PCInDB]:
        """Get all PCs, optionally filter by connection status"""
        db = get_database()
        query = {"connected": True} if connected_only else {}
        cursor = db.pcs.find(query).sort("last_seen", -1)
        pcs = []
        async for pc_data in cursor:
            pc_data["_id"] = str(pc_data["_id"])
            pcs.append(PCInDB(**pc_data))
        return pcs
    
    @staticmethod
    async def create_or_update_pc(pc_id: str, name: Optional[str] = None, 
                                   ip_address: Optional[str] = None,
                                   hostname: Optional[str] = None,
                                   os_info: Optional[dict] = None,
                                   metadata: Optional[dict] = None) -> PCInDB:
        """Create or update a PC"""
        db = get_database()
        now = datetime.utcnow()
        
        # Check if PC exists
        existing_pc = await db.pcs.find_one({"pc_id": pc_id})
        
        update_data = {
            "pc_id": pc_id,
            "name": name or pc_id,
            "connected": True,
            "last_seen": now,
            "metadata": metadata or {}
        }
        
        # Only update fields if they are provided (not None)
        # This prevents overwriting existing values with None
        # ALWAYS update IP if provided (even if PC already exists)
        if ip_address is not None:
            update_data["ip_address"] = ip_address
            logger.info(f"Updating IP address for {pc_id}: {ip_address}")
        elif not existing_pc:
            # Only set to None if PC is new
            update_data["ip_address"] = None
            
        if hostname is not None:
            update_data["hostname"] = hostname
        elif not existing_pc:
            update_data["hostname"] = None
            
        if os_info is not None:
            update_data["os_info"] = os_info
        elif not existing_pc:
            update_data["os_info"] = None
        
        # Only set connected_at if PC is new
        if not existing_pc:
            update_data["connected_at"] = now
        else:
            # Preserve existing connected_at if already connected
            if not existing_pc.get("connected", False):
                update_data["connected_at"] = now
        
        result = await db.pcs.find_one_and_update(
            {"pc_id": pc_id},
            {"$set": update_data},
            upsert=True,
            return_document=True
        )
        
        result["_id"] = str(result["_id"])
        return PCInDB(**result)
    
    @staticmethod
    async def update_connection_status(pc_id: str, connected: bool) -> Optional[PCInDB]:
        """Update PC connection status"""
        db = get_database()
        now = datetime.utcnow()
        
        update_data = {
            "connected": connected,
            "last_seen": now
        }
        
        if connected:
            # When setting connected to true, also set connected_at
            # But only if it's not already set or if PC was previously disconnected
            existing_pc = await db.pcs.find_one({"pc_id": pc_id})
            if not existing_pc or not existing_pc.get("connected", False):
                update_data["connected_at"] = now
        
        result = await db.pcs.find_one_and_update(
            {"pc_id": pc_id},
            {"$set": update_data},
            upsert=True,  # Create PC if it doesn't exist
            return_document=True
        )
        
        if result:
            result["_id"] = str(result["_id"])
            logger.debug(f"Updated connection status for {pc_id}: connected={connected}")
            return PCInDB(**result)
        return None
    
    @staticmethod
    async def update_last_seen(pc_id: str) -> Optional[PCInDB]:
        """Update PC last seen timestamp and ensure connected status is true"""
        db = get_database()
        # Update both last_seen and connected status
        # If PC is sending messages, it's definitely connected
        result = await db.pcs.find_one_and_update(
            {"pc_id": pc_id},
            {"$set": {
                "last_seen": datetime.utcnow(),
                "connected": True  # Ensure connected is true when updating last_seen
            }},
            return_document=True
        )
        
        if result:
            result["_id"] = str(result["_id"])
            return PCInDB(**result)
        return None
    
    @staticmethod
    async def delete_pc(pc_id: str) -> bool:
        """Delete a PC"""
        db = get_database()
        result = await db.pcs.delete_one({"pc_id": pc_id})
        return result.deleted_count > 0
    
    @staticmethod
    async def get_connected_count() -> int:
        """Get count of connected PCs"""
        db = get_database()
        return await db.pcs.count_documents({"connected": True})

