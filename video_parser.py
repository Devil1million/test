"""
Advanced Auto Caption Bot - Video Parser Utility
Intelligent anime information extraction from filenames and captions
"""

import re
import asyncio
from typing import Optional, Dict, Tuple
from pathlib import Path
import logging

logger = logging.getLogger("VideoParser")


class VideoParser:
    """Parse anime information from video files"""
    
    # Compiled regex patterns for better performance
    PATTERNS = [
        # [SubsPlease] Anime Name - S01E07 [720p]
        re.compile(r'\[?([^\]]+)\]?\s*-?\s*S?(\d+)[xE](\d+)\s*\[?(\d+p)?\]?', re.IGNORECASE),
        
        # Anime.Name.S01.E07.720p.WEB-DL
        re.compile(r'([A-Za-z.\s]+?)\.S(\d+)\.E(\d+)\.(\d+p)', re.IGNORECASE),
        
        # Anime Name - 01x07 - 720p
        re.compile(r'([A-Za-z\s]+?)\s*-?\s*(\d+)x(\d+)\s*-?\s*(\d+p)?', re.IGNORECASE),
        
        # [Group] Anime Name - 07 [1080p]
        re.compile(r'\[([^\]]+)\]\s*([A-Za-z\s]+)\s*-\s*(\d+)\s*\[(\d+p)\]', re.IGNORECASE),
        
        # Anime_Name_E07_720p
        re.compile(r'([A-Za-z_\s]+)_E(\d+)_(\d+p)', re.IGNORECASE),
        
        # Fairy Tail 175 [720p]
        re.compile(r'([A-Za-z\s]+)\s+(\d{1,3})\s+\[?(\d+p)\]?', re.IGNORECASE),
    ]
    
    def __init__(self):
        self.cache = {}
    
    def clean_anime_name(self, name: str) -> str:
        """Clean and normalize anime name"""
        # Remove common prefixes
        name = re.sub(r'^\[.*?\]\s*', '', name)
        
        # Replace dots and underscores with spaces
        name = name.replace('.', ' ').replace('_', ' ')
        
        # Remove extra spaces
        name = ' '.join(name.split())
        
        # Title case
        name = name.title()
        
        return name.strip()
    
    def extract_from_text(self, text: str) -> Optional[Dict]:
        """Extract anime info from text using regex patterns"""
        if not text:
            return None
        
        for pattern in self.PATTERNS:
            match = pattern.search(text)
            if match:
                groups = match.groups()
                
                try:
                    # Different patterns have different group structures
                    if len(groups) == 4:
                        # Pattern with name, season, episode, quality
                        anime_name = self.clean_anime_name(groups[0])
                        season = int(groups[1]) if groups[1] else 1
                        episode = int(groups[2]) if groups[2] else 1
                        quality = groups[3] if groups[3] else None
                    elif len(groups) == 3:
                        # Pattern with name, episode, quality (no season)
                        anime_name = self.clean_anime_name(groups[0])
                        season = 1
                        episode = int(groups[1]) if groups[1] else 1
                        quality = groups[2] if groups[2] else None
                    else:
                        continue
                    
                    return {
                        "anime_name": anime_name,
                        "season": season,
                        "episode": episode,
                        "quality": quality,
                        "confidence": 0.8  # Base confidence
                    }
                except (ValueError, IndexError) as e:
                    logger.debug(f"Pattern match failed: {e}")
                    continue
        
        return None
    
    def cross_verify(self, filename_data: Optional[Dict], 
                     caption_data: Optional[Dict]) -> Dict:
        """Cross-verify data from filename and caption"""
        if not filename_data and not caption_data:
            raise ValueError("No anime information found in filename or caption")
        
        if not filename_data:
            return caption_data
        
        if not caption_data:
            return filename_data
        
        # Both exist - cross verify
        verified = filename_data.copy()
        
        # Check if anime names match (fuzzy)
        if filename_data["anime_name"].lower() == caption_data["anime_name"].lower():
            verified["confidence"] = 1.0  # Perfect match
        else:
            # Use filename data but lower confidence
            verified["confidence"] = 0.6
        
        # Verify episode number
        if filename_data["episode"] != caption_data["episode"]:
            logger.warning(f"Episode mismatch: filename={filename_data['episode']}, "
                          f"caption={caption_data['episode']}")
        
        # Verify quality if both have it
        if filename_data.get("quality") and caption_data.get("quality"):
            if filename_data["quality"] != caption_data["quality"]:
                logger.warning(f"Quality mismatch: filename={filename_data['quality']}, "
                              f"caption={caption_data['quality']}")
        
        # Use caption quality if filename doesn't have it
        if not verified.get("quality") and caption_data.get("quality"):
            verified["quality"] = caption_data["quality"]
        
        return verified
    
    async def extract_anime_info(self, filename: str, caption: str = "") -> Dict:
        """
        Main extraction function
        Returns: {anime_name, season, episode, quality, confidence}
        """
        # Check cache first
        cache_key = f"{filename}:{caption}"
        if cache_key in self.cache:
            logger.debug(f"Cache hit for: {cache_key}")
            return self.cache[cache_key]
        
        # Extract from filename
        filename_data = self.extract_from_text(filename)
        logger.debug(f"Filename extraction: {filename_data}")
        
        # Extract from caption
        caption_data = self.extract_from_text(caption) if caption else None
        logger.debug(f"Caption extraction: {caption_data}")
        
        # Cross verify
        verified_data = self.cross_verify(filename_data, caption_data)
        
        # Cache result
        self.cache[cache_key] = verified_data
        
        logger.info(f"✅ Extracted: {verified_data['anime_name']} S{verified_data['season']:02d}E{verified_data['episode']:02d}")
        
        return verified_data
    
    async def verify_quality_from_metadata(self, video_metadata: Dict) -> str:
        """Determine quality from video resolution"""
        height = video_metadata.get("height", 0)
        
        # Quality mapping based on height
        if height <= 480:
            return "480p"
        elif height <= 720:
            return "720p"
        elif height <= 1080:
            return "1080p"
        elif height <= 2160:
            return "4K"
        else:
            return "8K"
    
    async def get_video_metadata(self, video_path: str) -> Dict:
        """Get video metadata using FFmpeg"""
        try:
            import ffmpeg
            
            probe = ffmpeg.probe(video_path)
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            
            if not video_stream:
                return {}
            
            metadata = {
                "width": int(video_stream.get('width', 0)),
                "height": int(video_stream.get('height', 0)),
                "duration": float(probe['format'].get('duration', 0)),
                "size": int(probe['format'].get('size', 0)),
                "bitrate": int(probe['format'].get('bit_rate', 0)),
                "codec": video_stream.get('codec_name', 'unknown')
            }
            
            return metadata
        except Exception as e:
            logger.error(f"❌ FFmpeg metadata extraction failed: {e}")
            return {}


class CaptionFormatter:
    """Format captions with variable replacement"""
    
    @staticmethod
    def apply_caption(video_data: Dict, caption_format: str) -> str:
        """
        Apply caption format with variables
        
        Variables:
        {a} = Anime Name
        {s} = Season Number (padded)
        {e} = Episode Number (padded)
        {q} = Quality
        [B] = Bold formatting marker
        """
        caption = caption_format
        
        # Replace variables
        caption = caption.replace("{a}", video_data.get("anime_name", "Unknown"))
        caption = caption.replace("{s}", str(video_data.get("season", 1)).zfill(2))
        caption = caption.replace("{e}", str(video_data.get("episode", 1)).zfill(2))
        caption = caption.replace("{q}", video_data.get("quality", "Unknown"))
        
        # Apply bold formatting
        if "[B]" in caption:
            parts = caption.split("[B]", 1)
            if len(parts) == 2:
                caption = parts[0] + "**" + parts[1] + "**"
        
        return caption
    
    @staticmethod
    def validate_format(caption_format: str) -> Tuple[bool, str]:
        """Validate caption format"""
        # Check for valid variables
        valid_vars = ["{a}", "{s}", "{e}", "{q}", "[B]"]
        
        # Extract all variables from format
        import re
        found_vars = re.findall(r'\{[aseq]\}|\[B\]', caption_format)
        
        # Check for invalid variables
        for var in found_vars:
            if var not in valid_vars:
                return False, f"Invalid variable: {var}"
        
        # Must have at least anime name
        if "{a}" not in caption_format:
            return False, "Caption must include anime name variable {a}"
        
        return True, "Valid caption format"


# Create singleton instances
video_parser = VideoParser()
caption_formatter = CaptionFormatter()


if __name__ == "__main__":
    # Test video parser
    async def test():
        parser = VideoParser()
        
        test_cases = [
            ("Fairy_Tail_S01E07_720p.mkv", ""),
            ("[SubsPlease] Demon Slayer - 01 [1080p].mkv", "Demon Slayer Episode 1"),
            ("Naruto.Shippuden.S01.E175.1080p.WEB-DL.mkv", ""),
            ("One Piece 1000 [720p].mp4", "One Piece #1000"),
        ]
        
        print("🧪 Testing Video Parser...\n")
        
        for filename, caption in test_cases:
            try:
                result = await parser.extract_anime_info(filename, caption)
                print(f"✅ {filename}")
                print(f"   └─ {result}\n")
            except Exception as e:
                print(f"❌ {filename}")
                print(f"   └─ Error: {e}\n")
        
        # Test caption formatter
        print("\n🧪 Testing Caption Formatter...\n")
        
        sample_data = {
            "anime_name": "Naruto",
            "season": 1,
            "episode": 5,
            "quality": "1080p"
        }
        
        format_template = "➥ {a} [{s}]\n Episode - {e}\n Quality : {q}\n [B]Powered by Bot"
        
        formatted = CaptionFormatter.apply_caption(sample_data, format_template)
        print(f"Format: {format_template}")
        print(f"\nResult:\n{formatted}")
    
    asyncio.run(test())
