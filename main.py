"""
RazeChan Bot - Main Runner
"""
import asyncio
import logging
from raze import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("RazeChan")

async def main():
    logger.info("🌸 RazeChan Bot starting...")
    async with app:
        me = await app.get_me()
        logger.info(f"✅ Logged in as @{me.username} | {me.first_name}")
        logger.info("🎀 RazeChan is LIVE! Waiting for messages~")
        await asyncio.Event().wait()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
