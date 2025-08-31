import asyncio
import json
import websockets

async def test_murf_websocket():
    uri = "ws://localhost:8000/ws/llm-to-murf"
    
    async with websockets.connect(uri) as websocket:
        # Prepare test message
        message = {
            "text": "Hello, this is a test of the Murf WebSocket streaming!",
            "session_id": "test-session-123",
            "voice_id": "en-US-natalie"
        }
        
        # Send message
        await websocket.send(json.dumps(message))
        print(f"Sent: {message}")
        
        # Process responses
        try:
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get("type") == "llm_chunk":
                    print(f"LLM Chunk: {data['text']}")
                elif data.get("type") == "llm_complete":
                    print(f"\nLLM Response Complete: {data['text']}\n")
                elif data.get("type") == "tts_chunk":
                    print(f"TTS Chunk Received (is_final: {data.get('is_final', False)})")
                    if data.get("data", {}).get("audio"):
                        print(f"Base64 Audio (first 50 chars): {data['data']['audio'][:50]}...")
                elif data.get("type") == "error":
                    print(f"Error: {data.get('message', 'Unknown error')}")
                    break
                
                # Check if this is the final TTS chunk
                if data.get("type") == "tts_chunk" and data.get("is_final"):
                    print("\nTTS Streaming Complete!")
                    break
                    
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(test_murf_websocket())
