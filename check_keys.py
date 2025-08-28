#!/usr/bin/env python3
"""
Check current API key configuration and test them
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("=== Current API Key Configuration ===")
    
    assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY', 'Not set')
    murf_key = os.getenv('MURF_API_KEY', 'Not set')
    
    print(f"ASSEMBLYAI_API_KEY: {assemblyai_key[:12]}... (length: {len(assemblyai_key)})")
    print(f"MURF_API_KEY: {murf_key[:12]}... (length: {len(murf_key)})")
    
    print("\n=== Key Analysis ===")
    print("AssemblyAI keys typically:")
    print("- Are 32-40 characters long")
    print("- Contain alphanumeric characters")
    print("- Example: 74b14f3ee13343dead18e2f50392fe4a")
    
    print("\nMurf keys typically:")
    print("- May have different format")
    print("- Check Murf dashboard for correct format")
    
    print(f"\nCurrent AssemblyAI key length: {len(assemblyai_key)}")
    print(f"Current Murf key length: {len(murf_key)}")
    
    if len(assemblyai_key) > 10 and len(murf_key) > 10:
        print("\n=== SWAP RECOMMENDATION ===")
        print("To swap the keys, update your .env file with:")
        print(f"ASSEMBLYAI_API_KEY={murf_key}")
        print(f"MURF_API_KEY={assemblyai_key}")

if __name__ == "__main__":
    main()
