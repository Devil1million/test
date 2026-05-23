"""
Advanced Auto Caption Bot - Database Module
Handles all MongoDB operations with async Motor driver
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config.settings import config
import logging

logger = logging.getLogger("Database")


class Database:
    """Async MongoDB database handler"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(config.MONGODB_URI)
            self.db = self.client[config.DATABASE_NAME]
            
            # Create indexes for better performance
            await self._create_indexes()
            
            logger.info("✅ Connected to MongoDB successfully!")
            return True
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            return False
    
    async def _create_indexes(self):
        """Create database indexes"""
        try:
            # Users collection indexes
            await self.db.users.create_index("user_id", unique=True)
            await self.db.users.create_index("role")
            await self.db.users.create_index("login_expires")
            
            # Channels collection indexes
            await self.db.channels.create_index([("user_id", 1), ("channel_id", 1)], unique=True)
            
            # Scheduled posts indexes
            await self.db.scheduled_posts.create_index("user_id")
            await self.db.scheduled_posts.create_index("scheduled_time")
            await self.db.scheduled_posts.create_index("status")
            
            # Cache collection with TTL
            await self.db.cache.create_index("created_at", expireAfterSeconds=config.CACHE_TTL)
            
            logger.info("✅ Database indexes created!")
        except Exception as e:
            logger.error(f"❌ Index creation failed: {e}")
    
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("✅ Database connection closed")
    
    # ==================== USER OPERATIONS ====================
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        return await self.db.users.find_one({"user_id": user_id})
    
    async def create_user(self, user_id: int, role: str = config.UserRoles.LOGIN_USER,
                         username: str = None, first_name: str = None) -> bool:
        """Create new user"""
        try:
            user_data = {
                "user_id": user_id,
                "role": role,
                "username": username,
                "first_name": first_name,
                "created_at": datetime.now(),
                "caption_format": config.DEFAULT_CAPTION,
                "active_channel": None,
                "total_videos": 0,
                "last_activity": datetime.now()
            }
            
            if role == config.UserRoles.LOGIN_USER:
                user_data["login_expires"] = datetime.now() + timedelta(hours=config.LOGIN_EXPIRY_HOURS)
            
            await self.db.users.insert_one(user_data)
            logger.info(f"✅ User {user_id} created with role {role}")
            return True
        except Exception as e:
            logger.error(f"❌ User creation failed: {e}")
            return False
    
    async def update_user_role(self, user_id: int, new_role: str) -> bool:
        """Update user role"""
        try:
            result = await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"role": new_role, "updated_at": datetime.now()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Role update failed: {e}")
            return False
    
    async def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        # Owner always authorized
        if user_id == config.OWNER_ID:
            return True
        
        user = await self.get_user(user_id)
        if not user:
            return False
        
        # Check login expiry for LOGIN_USER
        if user["role"] == config.UserRoles.LOGIN_USER:
            if datetime.now() > user.get("login_expires", datetime.min):
                await self.db.users.delete_one({"user_id": user_id})
                logger.info(f"🕒 Login expired for user {user_id}")
                return False
        
        return True
    
    async def get_user_role(self, user_id: int) -> Optional[str]:
        """Get user role"""
        if user_id == config.OWNER_ID:
            return config.UserRoles.OWNER
        
        user = await self.get_user(user_id)
        return user["role"] if user else None
    
    async def cleanup_expired_logins(self):
        """Remove expired login users"""
        try:
            result = await self.db.users.delete_many({
                "role": config.UserRoles.LOGIN_USER,
                "login_expires": {"$lt": datetime.now()}
            })
            if result.deleted_count > 0:
                logger.info(f"🧹 Cleaned up {result.deleted_count} expired login users")
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    async def get_all_admins(self) -> List[Dict]:
        """Get all admin users"""
        cursor = self.db.users.find({"role": config.UserRoles.ADMIN})
        return await cursor.to_list(length=None)
    
    async def get_all_users_count(self) -> Dict[str, int]:
        """Get user count by role"""
        pipeline = [
            {"$group": {"_id": "$role", "count": {"$sum": 1}}}
        ]
        results = await self.db.users.aggregate(pipeline).to_list(length=None)
        return {item["_id"]: item["count"] for item in results}
    
    # ==================== CAPTION OPERATIONS ====================
    
    async def set_caption(self, user_id: int, caption_format: str) -> bool:
        """Set user's caption format"""
        try:
            result = await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"caption_format": caption_format, "updated_at": datetime.now()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Caption update failed: {e}")
            return False
    
    async def get_caption(self, user_id: int) -> str:
        """Get user's caption format"""
        user = await self.get_user(user_id)
        return user.get("caption_format", config.DEFAULT_CAPTION) if user else config.DEFAULT_CAPTION
    
    # ==================== CHANNEL OPERATIONS ====================
    
    async def add_channel(self, user_id: int, channel_id: int, channel_name: str) -> bool:
        """Add channel for user"""
        try:
            channel_data = {
                "user_id": user_id,
                "channel_id": channel_id,
                "channel_name": channel_name,
                "added_at": datetime.now(),
                "total_posts": 0,
                "last_post": None
            }
            await self.db.channels.insert_one(channel_data)
            
            # Set as active if first channel
            user = await self.get_user(user_id)
            if not user.get("active_channel"):
                await self.set_active_channel(user_id, channel_id)
            
            logger.info(f"✅ Channel {channel_id} added for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Channel addition failed: {e}")
            return False
    
    async def remove_channel(self, user_id: int, channel_id: int) -> bool:
        """Remove channel for user"""
        try:
            result = await self.db.channels.delete_one({
                "user_id": user_id,
                "channel_id": channel_id
            })
            
            # Update active channel if removed
            user = await self.get_user(user_id)
            if user.get("active_channel") == channel_id:
                # Get another channel if exists
                channels = await self.get_user_channels(user_id)
                new_active = channels[0]["channel_id"] if channels else None
                await self.set_active_channel(user_id, new_active)
            
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"❌ Channel removal failed: {e}")
            return False
    
    async def get_user_channels(self, user_id: int) -> List[Dict]:
        """Get all channels for user"""
        cursor = self.db.channels.find({"user_id": user_id})
        return await cursor.to_list(length=None)
    
    async def set_active_channel(self, user_id: int, channel_id: Optional[int]) -> bool:
        """Set active channel for user"""
        try:
            result = await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"active_channel": channel_id, "updated_at": datetime.now()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Active channel update failed: {e}")
            return False
    
    async def get_active_channel(self, user_id: int) -> Optional[int]:
        """Get user's active channel"""
        user = await self.get_user(user_id)
        return user.get("active_channel") if user else None
    
    async def increment_channel_posts(self, channel_id: int):
        """Increment channel post count"""
        await self.db.channels.update_one(
            {"channel_id": channel_id},
            {
                "$inc": {"total_posts": 1},
                "$set": {"last_post": datetime.now()}
            }
        )
    
    # ==================== SCHEDULED POSTS ====================
    
    async def add_scheduled_post(self, user_id: int, channel_id: int, 
                                 video_file_id: str, caption: str, 
                                 scheduled_time: datetime) -> Optional[str]:
        """Add scheduled post"""
        try:
            post_data = {
                "user_id": user_id,
                "channel_id": channel_id,
                "video_file_id": video_file_id,
                "caption": caption,
                "scheduled_time": scheduled_time,
                "status": "pending",
                "created_at": datetime.now()
            }
            result = await self.db.scheduled_posts.insert_one(post_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"❌ Scheduled post creation failed: {e}")
            return None
    
    async def get_pending_posts(self) -> List[Dict]:
        """Get posts ready to be sent"""
        return await self.db.scheduled_posts.find({
            "status": "pending",
            "scheduled_time": {"$lte": datetime.now()}
        }).to_list(length=None)
    
    async def mark_post_sent(self, post_id: str):
        """Mark scheduled post as sent"""
        from bson import ObjectId
        await self.db.scheduled_posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": {"status": "sent", "sent_at": datetime.now()}}
        )
    
    async def get_user_scheduled_posts(self, user_id: int) -> List[Dict]:
        """Get user's scheduled posts"""
        return await self.db.scheduled_posts.find({
            "user_id": user_id,
            "status": "pending"
        }).sort("scheduled_time", 1).to_list(length=None)
    
    async def cancel_scheduled_post(self, post_id: str, user_id: int) -> bool:
        """Cancel scheduled post"""
        from bson import ObjectId
        result = await self.db.scheduled_posts.delete_one({
            "_id": ObjectId(post_id),
            "user_id": user_id
        })
        return result.deleted_count > 0
    
    # ==================== CACHE OPERATIONS ====================
    
    async def cache_set(self, key: str, value: Any):
        """Set cache value"""
        await self.db.cache.update_one(
            {"key": key},
            {"$set": {"value": value, "created_at": datetime.now()}},
            upsert=True
        )
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get cache value"""
        result = await self.db.cache.find_one({"key": key})
        return result["value"] if result else None
    
    # ==================== STATISTICS ====================
    
    async def get_bot_stats(self) -> Dict:
        """Get bot statistics"""
        total_users = await self.db.users.count_documents({})
        total_channels = await self.db.channels.count_documents({})
        total_scheduled = await self.db.scheduled_posts.count_documents({"status": "pending"})
        
        # Total videos processed
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_videos"}}}]
        result = await self.db.users.aggregate(pipeline).to_list(1)
        total_videos = result[0]["total"] if result else 0
        
        return {
            "total_users": total_users,
            "total_channels": total_channels,
            "total_videos": total_videos,
            "total_scheduled": total_scheduled
        }
    
    async def increment_user_videos(self, user_id: int):
        """Increment user's video count"""
        await self.db.users.update_one(
            {"user_id": user_id},
            {
                "$inc": {"total_videos": 1},
                "$set": {"last_activity": datetime.now()}
            }
        )


# Create singleton instance
db = Database()


# Background tasks
async def start_background_tasks():
    """Start background cleanup tasks"""
    import asyncio
    
    async def cleanup_loop():
        while True:
            await asyncio.sleep(3600)  # Every hour
            await db.cleanup_expired_logins()
    
    asyncio.create_task(cleanup_loop())


if __name__ == "__main__":
    # Test database connection
    import asyncio
    
    async def test():
        connected = await db.connect()
        if connected:
            print("✅ Database connection successful!")
            
            # Test operations
            test_user_id = 123456789
            await db.create_user(test_user_id, config.UserRoles.ADMIN)
            user = await db.get_user(test_user_id)
            print(f"📊 User created: {user}")
            
            await db.close()
        else:
            print("❌ Database connection failed!")
    
    asyncio.run(test())
