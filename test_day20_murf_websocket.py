#!/usr/bin/env python3
"""
Test script for Day 20: Murf WebSocket TTS integration
Tests the streaming LLM response to Murf WebSocket functionality
"""
import asyncio
import json
import websockets
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_llm_murf_websocket():
    """Test the LLM streaming with Murf WebSocket TTS integration."""
    
    # Connect to the LLM streaming WebSocket endpoint
    uri = "ws://localhost:8000/ws/llm-stream"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to LLM streaming WebSocket")
            
            # Send a test message
            test_message = {
                "text": "Tell me a short joke about artificial intelligence",
                "session_id": "test-day20-session",
                "voice_id": "en-US-natalie"
            }
            
            logger.info(f"📤 Sending test message: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Listen for responses
            message_count = 0
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)
                    message_count += 1
                    
                    logger.info(f"📥 Message {message_count}: {data.get('type', 'unknown')}")
                    
                    if data.get("type") == "start":
                        print("LLM streaming started")
                        
                    elif data.get("type") == "chunk":
                        print(f"LLM chunk: {data.get('text', '')}", end='', flush=True)
                        
                    elif data.get("type") == "end":
                        print(f"\nLLM streaming completed. Full response: {data.get('text', '')}")
                        
                    elif data.get("type") == "tts_start":
                        print("Murf WebSocket TTS started")
                        
                    elif data.get("type") == "tts_chunk":
                        tts_data = data.get("data", {})
                        if "audio" in tts_data:
                            audio_length = len(tts_data["audio"])
                            print(f"Received TTS audio chunk: {audio_length} chars")
                            # This will trigger the base64 logging in the TTS service
                        
                    elif data.get("type") == "tts_complete":
                        print("Murf WebSocket TTS completed")
                        break
                        
                    elif data.get("type") == "error" or data.get("type") == "tts_error":
                        print(f"Error: {data.get('message', 'Unknown error')}")
                        break
                        
                except asyncio.TimeoutError:
                    logger.error("⏰ Timeout waiting for response")
                    break
                except Exception as e:
                    logger.error(f"❌ Error receiving message: {e}")
                    break
                    
            logger.info(f"📊 Test completed. Received {message_count} messages")
            
    except Exception as e:
        logger.error(f"❌ Connection error: {e}")
        print("Make sure the server is running on http://localhost:8000")

if __name__ == "__main__":
    print("Testing Day 20: LLM Streaming + Murf WebSocket TTS")
    print("=" * 60)
    asyncio.run(test_llm_murf_websocket())
