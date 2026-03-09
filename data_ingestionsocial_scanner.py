"""
Social Momentum Detector: Monitors Twitter/X and Telegram for memecoin momentum signals.
Uses bird CLI for Twitter and BeautifulSoup for Telegram scraping.
"""
import asyncio
import aiohttp
import subprocess
import json
import re
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from bs4 import BeautifulSoup
from loguru import logger

from firebase_setup import get_firestore
from config import settings

@dataclass
class SocialSignal:
    """Structured social signal data class."""
    platform: str
    coin_symbol: str
    contract_address: Optional[str]
    mention_count: int
    unique_users: int
    sentiment_score: float
    timestamp: datetime
    raw_text: str
    signal_id: str

class SocialMomentumDetector:
    """Detects memecoin momentum across social platforms."""
    
    def __init__(self):
        self.db = get_firestore()
        self.seen_signals: Set[str] = set()
        self.contract_pattern = re.compile(r'0x[a-fA-F0-9]{40}')
        
        # Initialize platform-specific clients
        self.twitter_available = self._check_twitter_cli()
        logger.info(f"Twitter CLI available: {self.twitter_available}")
    
    def _check_twitter_cli(self) -> bool:
        """Check if bird CLI is installed."""
        try:
            result = subprocess.run(['which', 'bird'], 
                                  capture_output=True, 
                                  text=True)
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Failed to check bird CLI: {e}")
            return False
    
    async def scan_twitter_keywords(self, keywords: List[str]) -> List[SocialSignal]:
        """
        Scan Twitter for keyword mentions using bird CLI.
        Keywords: ['base', 'memecoin', 'degen', 'gm', 'wagmi', 'new', 'launch']
        """
        signals = []
        
        if not self.twitter_available:
            logger.warning("Twitter CLI not available, skipping Twitter scan")
            return signals
        
        for keyword in keywords:
            try:
                # Use bird CLI to search recent tweets
                cmd = ['bird', 'search', f'"{keyword}"', '--limit', '50', '--json']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    logger.error(f"bird CLI failed for keyword {keyword}: {result.stderr}")
                    continue
                
                tweets = json.loads(result.stdout)
                
                for tweet in tweets:
                    signal = self._parse_tweet_to_signal(tweet, keyword)
                    if signal and signal.signal_id not in self.seen_signals:
                        signals.append(signal)
                        self.seen_signals.add(signal.signal_id)
                        
            except subprocess.TimeoutExpired:
                logger.error(f"Twitter scan timeout for keyword: {keyword}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Twitter JSON for {keyword}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error scanning Twitter for {keyword}: {e}")
        
        return signals
    
    def _parse_tweet_to_signal(self, tweet: Dict, keyword: str) -> Optional[SocialSignal]:
        """Convert raw tweet to structured SocialSignal."""
        try:
            text = tweet.get('text', '').lower()
            user = tweet.get('user', {}).get('screen_name', '')
            tweet_id = tweet.get('id_str', '')
            
            # Extract potential contract address
            contract_match = self.contract_pattern.search(text)
            contract_address = contract_match.group(0) if contract_match else None
            
            # Calculate basic metrics
            retweet_count = tweet.get('retweet_count', 0)
            favorite_count = tweet.get('favorite_count', 0)
            mention_count = retweet_count + favorite_count
            
            # Simple sentiment scoring
            positive_words = ['moon', 'pump', 'bullish', 'buy', 'gem', 'alpha']
            negative_words = ['scam', 'rug', 'sell', 'bearish', 'dump']
            
            sentiment = 0.5  # Neutral baseline
            for word in positive_words:
                if word in text:
                    sentiment += 0.1
            for word in negative_words:
                if word in text:
                    sentiment -= 0.1
            
            # Clamp sentiment between 0 and 1
            sentiment = max(0.0, min(1.0, sentiment))
            
            signal = SocialSignal(
                platform='twitter',
                coin_symbol=self._extract_coin_symbol(text),
                contract_address=contract_address,
                mention_count=mention_count,
                unique_users=1,  # Would need user tracking for accurate count
                sentiment_score=sentiment,
                timestamp=datetime.now(),
                raw_text=text[:500],  # Truncate for storage
                signal_id=f"twitter_{tweet_id}"
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Failed to parse tweet: {e}")
            return None
    
    def _extract_coin_symbol(self, text: str) -> str:
        """Extract potential coin symbol from text."""
        # Simple pattern for coin symbols (all caps, 2-5 chars)
        symbol_pattern = re.compile(r'\b[A-Z]{2,5}\b')
        matches = symbol_pattern.findall(text)
        return matches[0] if matches else 'UNKNOWN'
    
    async def save_signals_to_firestore(self, signals: List[SocialSignal]) -> None:
        """Save detected signals to Firestore for processing."""
        if not signals:
            return
        
        batch = self.db.batch()
        signals_ref = self.db.collection('signals')
        
        for signal in signals:
            doc_ref = signals_ref.document(signal.signal_id)
            data = {
                'platform': signal.platform,
                'coin_symbol': signal.coin_symbol,
                'contract_address': signal.contract_address,
                'mention_count': signal.mention_count,
                'unique_users': signal.unique_users,
                'sentiment_score': signal.sentiment_score,
                'timestamp': signal.timestamp,
                'raw_text': signal.raw_text,
                'processed': False,
                'score': 0.0,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            batch.set(doc_ref, data, merge=True)
        
        try:
            await asyncio.to_thread(batch.commit)
            logger.info(f"Saved {len(signals)} signals to Firestore")
        except Exception as e:
            logger.error(f"Failed to save signals to Firestore: {e}")
    
    async def run_scan_cycle(self) -> None:
        """Main scanning cycle - to be run periodically."""
        keywords = ['base', 'memecoin', 'degen', 'gm', 'wagmi', 'new', 'launch']
        
        logger.info("Starting social media scan cycle")
        
        # Scan Twitter
        twitter_signals = await self.scan_twitter_keywords(keywords)
        
        # Save all signals
        all_signals = twitter_signals
        await self.save_signals_to_firestore(all_signals)
        
        logger.info(f"Scan cycle completed. Found {len(all_signals)} new signals")

async def main():
    """Test function for social scanner."""
    detector = SocialMomentumDetector()
    await detector.run_scan_cycle()

if __name__ == "__main__":
    asyncio.run(main())