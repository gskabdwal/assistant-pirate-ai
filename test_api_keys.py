#!/usr/bin/env python3
"""
Script to test and identify correct API keys for AssemblyAI and Murf
"""
import asyncio
import httpx
from assemblyai import Transcriber

async def test_assemblyai_key(api_key: str) -> dict:
    """Test if a key works with AssemblyAI"""
    try:
        print(f"Testing AssemblyAI with key: {api_key[:8]}...")
        transcriber = Transcriber(api_key=api_key)
        # Try to list models - this will fail if key is invalid
        models = transcriber.get_transcription_models()
        if models and isinstance(models, list):
            return {'valid': True, 'service': 'AssemblyAI', 'message': 'Key works with AssemblyAI'}
        return {'valid': False, 'service': 'AssemblyAI', 'message': 'Key invalid for AssemblyAI'}
    except Exception as e:
        return {'valid': False, 'service': 'AssemblyAI', 'message': f'Error: {str(e)}'}

async def test_murf_key(api_key: str) -> dict:
    """Test if a key works with Murf"""
    try:
        print(f"Testing Murf with key: {api_key[:8]}...")
        url = "https://api.murf.ai/v1/voices"
        headers = {"api-key": api_key}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                return {'valid': True, 'service': 'Murf', 'message': 'Key works with Murf'}
            return {'valid': False, 'service': 'Murf', 'message': f'HTTP {response.status_code}: {response.text[:100]}'}
    except Exception as e:
        return {'valid': False, 'service': 'Murf', 'message': f'Error: {str(e)}'}

async def main():
    print("=== API Key Tester ===")
    print("Enter your two API keys to test which one belongs to which service:")
    
    key1 = input("Enter first API key: ").strip()
    key2 = input("Enter second API key: ").strip()
    
    print("\n=== Testing Key 1 ===")
    assemblyai_result1 = await test_assemblyai_key(key1)
    murf_result1 = await test_murf_key(key1)
    
    print(f"Key 1 with AssemblyAI: {assemblyai_result1['message']}")
    print(f"Key 1 with Murf: {murf_result1['message']}")
    
    print("\n=== Testing Key 2 ===")
    assemblyai_result2 = await test_assemblyai_key(key2)
    murf_result2 = await test_murf_key(key2)
    
    print(f"Key 2 with AssemblyAI: {assemblyai_result2['message']}")
    print(f"Key 2 with Murf: {murf_result2['message']}")
    
    print("\n=== RESULTS ===")
    if assemblyai_result1['valid']:
        print(f"✅ Key 1 ({key1[:8]}...) is your AssemblyAI key")
    if assemblyai_result2['valid']:
        print(f"✅ Key 2 ({key2[:8]}...) is your AssemblyAI key")
    
    if murf_result1['valid']:
        print(f"✅ Key 1 ({key1[:8]}...) is your Murf key")
    if murf_result2['valid']:
        print(f"✅ Key 2 ({key2[:8]}...) is your Murf key")
    
    print("\n=== RECOMMENDED .env CONFIGURATION ===")
    if assemblyai_result1['valid']:
        print(f"ASSEMBLYAI_API_KEY={key1}")
    elif assemblyai_result2['valid']:
        print(f"ASSEMBLYAI_API_KEY={key2}")
    
    if murf_result1['valid']:
        print(f"MURF_API_KEY={key1}")
    elif murf_result2['valid']:
        print(f"MURF_API_KEY={key2}")

if __name__ == "__main__":
    asyncio.run(main())
