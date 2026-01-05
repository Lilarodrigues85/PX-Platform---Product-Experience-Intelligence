# US-003: Processamento de Eventos
# Consumer Kafka com enriquecimento e sessionization

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import httpx
import geoip2.database
from user_agents import parse

# Event processor
@dataclass
class ProcessedEvent:
    event_id: str
    tenant_id: str
    user_id: Optional[str]
    session_id: Optional[str]
    event_name: str
    timestamp: str
    properties: Dict[str, Any]
    
    # Enriched data
    geo_country: Optional[str] = None
    geo_city: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    
    # Processing metadata
    ingested_at: str = ""
    processed_at: str = ""
    session_start: Optional[str] = None
    session_duration: Optional[int] = None

class EventProcessor:
    def __init__(self):
        self.sessions = {}  # In production: use Redis
        self.processed_events = []  # In production: send to ClickHouse
        
    async def process_events(self, raw_events: List[Dict[str, Any]]) -> List[ProcessedEvent]:
        """Process batch of raw events"""
        processed = []
        
        for raw_event in raw_events:
            try:
                # 1. Enrich event
                enriched = await self.enrich_event(raw_event)
                
                # 2. Sessionize
                sessionized = await self.sessionize_event(enriched)
                
                # 3. Deduplicate
                if not self.is_duplicate(sessionized):
                    processed.append(sessionized)
                    
            except Exception as e:
                print(f"Error processing event {raw_event.get('event_id')}: {e}")
                continue
        
        # 4. Store in ClickHouse (simulated)
        await self.store_events(processed)
        
        return processed
    
    async def enrich_event(self, raw_event: Dict[str, Any]) -> ProcessedEvent:
        """Enrich event with geo, device, browser info"""
        
        # Extract user agent
        user_agent = raw_event.get('properties', {}).get('user_agent', '')
        parsed_ua = parse(user_agent) if user_agent else None
        
        # Extract IP (in production, get from request headers)
        ip_address = raw_event.get('properties', {}).get('ip_address', '127.0.0.1')
        
        # Geo enrichment (simplified)
        geo_data = await self.get_geo_data(ip_address)
        
        # Device detection
        device_type = self.detect_device_type(parsed_ua)
        
        processed_event = ProcessedEvent(
            event_id=raw_event['event_id'],
            tenant_id=raw_event['tenant_id'],
            user_id=raw_event.get('user_id'),
            session_id=raw_event.get('session_id'),
            event_name=raw_event['event_name'],
            timestamp=raw_event['timestamp'],
            properties=raw_event['properties'],
            
            # Enriched data
            geo_country=geo_data.get('country'),
            geo_city=geo_data.get('city'),
            device_type=device_type,
            browser=parsed_ua.browser.family if parsed_ua else None,
            os=parsed_ua.os.family if parsed_ua else None,
            
            # Processing metadata
            ingested_at=raw_event.get('ingested_at', ''),
            processed_at=datetime.utcnow().isoformat()
        )
        
        return processed_event
    
    async def sessionize_event(self, event: ProcessedEvent) -> ProcessedEvent:
        """Add session information to event"""
        
        if not event.session_id:
            return event
        
        session_key = f"{event.tenant_id}:{event.session_id}"
        current_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
        
        # Get or create session
        if session_key not in self.sessions:
            self.sessions[session_key] = {
                'start_time': current_time,
                'last_activity': current_time,
                'event_count': 0
            }
        
        session = self.sessions[session_key]
        
        # Update session
        session['last_activity'] = current_time
        session['event_count'] += 1
        
        # Calculate session duration
        duration = (current_time - session['start_time']).total_seconds()
        
        # Add session data to event
        event.session_start = session['start_time'].isoformat()
        event.session_duration = int(duration)
        
        # Session timeout (30 minutes)
        if duration > 1800:  # 30 minutes
            # Start new session
            self.sessions[session_key] = {
                'start_time': current_time,
                'last_activity': current_time,
                'event_count': 1
            }
            event.session_start = current_time.isoformat()
            event.session_duration = 0
        
        return event
    
    def is_duplicate(self, event: ProcessedEvent) -> bool:
        """Check if event is duplicate"""
        # Simple deduplication based on event_id
        event_hash = hashlib.md5(
            f"{event.event_id}{event.timestamp}".encode()
        ).hexdigest()
        
        # In production: check Redis cache
        # For now, assume no duplicates
        return False
    
    async def store_events(self, events: List[ProcessedEvent]):
        """Store events in ClickHouse (simulated)"""
        
        for event in events:
            # Convert to ClickHouse format
            clickhouse_event = {
                'event_id': event.event_id,
                'tenant_id': event.tenant_id,
                'user_id': event.user_id or '',
                'session_id': event.session_id or '',
                'event_name': event.event_name,
                'timestamp': event.timestamp,
                'properties': json.dumps(event.properties),
                'geo_country': event.geo_country or '',
                'geo_city': event.geo_city or '',
                'device_type': event.device_type or '',
                'browser': event.browser or '',
                'os': event.os or '',
                'ingested_at': event.ingested_at,
                'processed_at': event.processed_at
            }
            
            # In production: INSERT INTO ClickHouse
            self.processed_events.append(clickhouse_event)
            print(f"Stored event: {event.event_name} for tenant {event.tenant_id}")
    
    async def get_geo_data(self, ip_address: str) -> Dict[str, str]:
        """Get geo data from IP address"""
        # Simplified geo lookup
        # In production: use MaxMind GeoIP2 or similar
        
        if ip_address.startswith('127.') or ip_address.startswith('192.168.'):
            return {'country': 'US', 'city': 'Local'}
        
        # Mock geo data
        return {'country': 'BR', 'city': 'São Paulo'}
    
    def detect_device_type(self, parsed_ua) -> str:
        """Detect device type from user agent"""
        if not parsed_ua:
            return 'unknown'
        
        if parsed_ua.is_mobile:
            return 'mobile'
        elif parsed_ua.is_tablet:
            return 'tablet'
        elif parsed_ua.is_pc:
            return 'desktop'
        else:
            return 'unknown'

# Kafka Consumer (simulated)
class EventConsumer:
    def __init__(self):
        self.processor = EventProcessor()
        self.running = False
    
    async def start_consuming(self):
        """Start consuming events from queue"""
        self.running = True
        print("Event consumer started...")
        
        while self.running:
            # In production: consume from Kafka
            # For now, process from in-memory queue
            from src.api.events import event_queue
            
            if event_queue:
                batch = event_queue[:100]  # Process in batches of 100
                del event_queue[:100]
                
                if batch:
                    print(f"Processing batch of {len(batch)} events...")
                    processed = await self.processor.process_events(batch)
                    print(f"Successfully processed {len(processed)} events")
            
            await asyncio.sleep(1)  # Check every second
    
    def stop(self):
        """Stop consuming events"""
        self.running = False
        print("Event consumer stopped")

# Main consumer runner
async def main():
    """Run the event consumer"""
    consumer = EventConsumer()
    
    try:
        await consumer.start_consuming()
    except KeyboardInterrupt:
        consumer.stop()
        print("Consumer shutdown gracefully")

if __name__ == "__main__":
    asyncio.run(main())