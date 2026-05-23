"""
Advanced Auto Caption Bot - API Integration
MyAnimeList and TMDB API integration for anime verification
"""

import aiohttp
import asyncio
from typing import Optional, Dict, List
import logging
from config.settings import config
from database.mongodb import db

logger = logging.getLogger("APIIntegration")


class AnimeAPIClient:
    """Client for anime database APIs"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.mal_base_url = "https://api.jikan.moe/v4"
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.cache_ttl = config.CACHE_TTL
    
    async def create_session(self):
        """Create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
    
    async def __aenter__(self):
        await self.create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()
    
    # ==================== MYANIMELIST (JIKAN API) ====================
    
    async def search_mal(self, anime_name: str) -> Optional[Dict]:
        """
        Search MyAnimeList using Jikan API
        Returns: {title, title_english, mal_id, year, episodes, score}
        """
        cache_key = f"mal:{anime_name.lower()}"
        
        # Check cache
        cached = await db.cache_get(cache_key)
        if cached:
            logger.debug(f"MAL cache hit: {anime_name}")
            return cached
        
        try:
            await self.create_session()
            
            url = f"{self.mal_base_url}/anime"
            params = {
                "q": anime_name,
                "limit": 1,
                "order_by": "popularity"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("data") and len(data["data"]) > 0:
                        anime = data["data"][0]
                        
                        result = {
                            "title": anime.get("title", ""),
                            "title_english": anime.get("title_english") or anime.get("title", ""),
                            "mal_id": anime.get("mal_id"),
                            "year": anime.get("year"),
                            "episodes": anime.get("episodes"),
                            "score": anime.get("score"),
                            "type": anime.get("type"),
                            "status": anime.get("status"),
                            "source": "mal"
                        }
                        
                        # Cache result
                        await db.cache_set(cache_key, result)
                        
                        logger.info(f"✅ MAL found: {result['title_english']}")
                        return result
                    else:
                        logger.warning(f"⚠️ MAL: No results for '{anime_name}'")
                        return None
                else:
                    logger.error(f"❌ MAL API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ MAL search failed: {e}")
            return None
    
    async def get_mal_anime_by_id(self, mal_id: int) -> Optional[Dict]:
        """Get detailed anime info by MAL ID"""
        try:
            await self.create_session()
            
            url = f"{self.mal_base_url}/anime/{mal_id}/full"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data")
                else:
                    return None
        except Exception as e:
            logger.error(f"❌ MAL ID fetch failed: {e}")
            return None
    
    # ==================== TMDB API ====================
    
    async def search_tmdb(self, anime_name: str) -> Optional[Dict]:
        """
        Search TMDB for anime
        Returns: {name, original_name, tmdb_id, year, overview}
        """
        if not config.TMDB_API_KEY:
            logger.warning("⚠️ TMDB API key not configured")
            return None
        
        cache_key = f"tmdb:{anime_name.lower()}"
        
        # Check cache
        cached = await db.cache_get(cache_key)
        if cached:
            logger.debug(f"TMDB cache hit: {anime_name}")
            return cached
        
        try:
            await self.create_session()
            
            url = f"{self.tmdb_base_url}/search/tv"
            params = {
                "api_key": config.TMDB_API_KEY,
                "query": anime_name,
                "language": "en-US",
                "page": 1
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("results") and len(data["results"]) > 0:
                        show = data["results"][0]
                        
                        # Extract year from first_air_date
                        first_air_date = show.get("first_air_date", "")
                        year = int(first_air_date.split("-")[0]) if first_air_date else None
                        
                        result = {
                            "name": show.get("name", ""),
                            "original_name": show.get("original_name", ""),
                            "tmdb_id": show.get("id"),
                            "year": year,
                            "overview": show.get("overview", ""),
                            "popularity": show.get("popularity"),
                            "vote_average": show.get("vote_average"),
                            "source": "tmdb"
                        }
                        
                        # Cache result
                        await db.cache_set(cache_key, result)
                        
                        logger.info(f"✅ TMDB found: {result['name']}")
                        return result
                    else:
                        logger.warning(f"⚠️ TMDB: No results for '{anime_name}'")
                        return None
                else:
                    logger.error(f"❌ TMDB API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ TMDB search failed: {e}")
            return None
    
    # ==================== CROSS-VERIFICATION ====================
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity (simple word overlap)"""
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    async def verify_anime_name(self, anime_name: str) -> Dict:
        """
        Cross-verify anime name with both MAL and TMDB
        Returns best verified name and metadata
        """
        logger.info(f"🔍 Verifying anime: {anime_name}")
        
        # Search both APIs concurrently
        mal_task = self.search_mal(anime_name)
        tmdb_task = self.search_tmdb(anime_name)
        
        mal_result, tmdb_result = await asyncio.gather(mal_task, tmdb_task)
        
        # Determine best result
        verified_data = {
            "original_name": anime_name,
            "verified_name": anime_name,  # Default
            "mal_data": mal_result,
            "tmdb_data": tmdb_result,
            "confidence": 0.5  # Default low confidence
        }
        
        if mal_result and tmdb_result:
            # Both found - cross verify
            mal_name = mal_result["title_english"]
            tmdb_name = tmdb_result["name"]
            
            similarity = self.calculate_similarity(mal_name, tmdb_name)
            
            if similarity > 0.6:
                # Names match - high confidence
                verified_data["verified_name"] = mal_name
                verified_data["confidence"] = 0.95
                logger.info(f"✅ Cross-verified: {mal_name} (similarity: {similarity:.2f})")
            else:
                # Names differ - prefer MAL (more anime-specific)
                verified_data["verified_name"] = mal_name
                verified_data["confidence"] = 0.75
                logger.warning(f"⚠️ Name mismatch: MAL='{mal_name}' vs TMDB='{tmdb_name}'")
        
        elif mal_result:
            # Only MAL found
            verified_data["verified_name"] = mal_result["title_english"]
            verified_data["confidence"] = 0.85
            logger.info(f"✅ Verified via MAL: {verified_data['verified_name']}")
        
        elif tmdb_result:
            # Only TMDB found
            verified_data["verified_name"] = tmdb_result["name"]
            verified_data["confidence"] = 0.70
            logger.info(f"✅ Verified via TMDB: {verified_data['verified_name']}")
        
        else:
            # Neither found - use original
            logger.warning(f"⚠️ No verification found for: {anime_name}")
        
        return verified_data
    
    # ==================== BATCH OPERATIONS ====================
    
    async def verify_multiple_anime(self, anime_names: List[str]) -> Dict[str, Dict]:
        """Verify multiple anime names concurrently"""
        tasks = [self.verify_anime_name(name) for name in anime_names]
        results = await asyncio.gather(*tasks)
        
        return {
            anime_names[i]: results[i] 
            for i in range(len(anime_names))
        }


# Create singleton instance
anime_api = AnimeAPIClient()


# Utility functions
async def quick_verify_anime(anime_name: str) -> str:
    """Quick verification - returns verified name"""
    result = await anime_api.verify_anime_name(anime_name)
    return result["verified_name"]


async def get_anime_metadata(anime_name: str) -> Dict:
    """Get full metadata for anime"""
    result = await anime_api.verify_anime_name(anime_name)
    
    metadata = {
        "verified_name": result["verified_name"],
        "confidence": result["confidence"]
    }
    
    # Add MAL data if available
    if result.get("mal_data"):
        mal = result["mal_data"]
        metadata.update({
            "mal_id": mal.get("mal_id"),
            "episodes": mal.get("episodes"),
            "score": mal.get("score"),
            "year": mal.get("year"),
            "status": mal.get("status")
        })
    
    # Add TMDB data if available
    if result.get("tmdb_data"):
        tmdb = result["tmdb_data"]
        metadata.update({
            "tmdb_id": tmdb.get("tmdb_id"),
            "overview": tmdb.get("overview"),
            "popularity": tmdb.get("popularity")
        })
    
    return metadata


if __name__ == "__main__":
    # Test API integration
    async def test():
        async with AnimeAPIClient() as api:
            print("🧪 Testing Anime API Integration...\n")
            
            test_anime = [
                "Naruto",
                "Demon Slayer",
                "One Piece",
                "Fairy Tail"
            ]
            
            for anime in test_anime:
                print(f"🔍 Testing: {anime}")
                result = await api.verify_anime_name(anime)
                print(f"   ✅ Verified: {result['verified_name']}")
                print(f"   📊 Confidence: {result['confidence']:.2%}")
                print(f"   📚 MAL: {result['mal_data']['title'] if result['mal_data'] else 'N/A'}")
                print(f"   🎬 TMDB: {result['tmdb_data']['name'] if result['tmdb_data'] else 'N/A'}")
                print()
                
                # Rate limit to avoid API throttling
                await asyncio.sleep(1)
    
    asyncio.run(test())
