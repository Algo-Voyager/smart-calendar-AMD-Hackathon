#!/usr/bin/env python3
"""
Quick script to check if Llama-3.2-3B model is available
"""

import os
import sys
from pathlib import Path

def check_model_availability():
    """Check if the Llama-3.2-3B model is available"""
    
    print("🔍 Checking Llama-3.2-3B model availability...")
    
    # Expected model path
    model_path = "/home/user/Models/meta-llama/Llama-3.2-3B"
    
    print(f"Looking for model at: {model_path}")
    
    if os.path.exists(model_path):
        print("✅ Model directory found!")
        
        # Check for essential model files
        essential_files = [
            "config.json",
            "tokenizer.json", 
            "tokenizer_config.json"
        ]
        
        found_files = []
        missing_files = []
        
        for file in essential_files:
            file_path = os.path.join(model_path, file)
            if os.path.exists(file_path):
                found_files.append(file)
                print(f"  ✅ {file}")
            else:
                missing_files.append(file)
                print(f"  ❌ {file}")
        
        # Check for model weight files
        weight_extensions = [".bin", ".safetensors", ".pth"]
        weight_files = []
        
        for file in os.listdir(model_path):
            if any(file.endswith(ext) for ext in weight_extensions):
                weight_files.append(file)
        
        if weight_files:
            print(f"  ✅ Found {len(weight_files)} weight file(s)")
            for weight_file in weight_files[:3]:  # Show first 3
                print(f"    - {weight_file}")
            if len(weight_files) > 3:
                print(f"    ... and {len(weight_files) - 3} more")
        else:
            print("  ❌ No weight files found")
            missing_files.append("model weights")
        
        # Summary
        if not missing_files:
            print("\n🎉 Model appears to be complete and ready!")
            return True
        else:
            print(f"\n⚠️  Model directory exists but missing: {', '.join(missing_files)}")
            return False
            
    else:
        print("❌ Model directory not found!")
        
        # Try to find alternative locations
        possible_paths = [
            "/Models/meta-llama/Llama-3.2-3B",
            "/home/user/models/meta-llama/Llama-3.2-3B",
            "/home/user/Models/meta-llama/Llama-3.2-3B",
            "/opt/models/meta-llama/Llama-3.2-3B"
        ]
        
        print("\n🔍 Searching alternative locations...")
        for alt_path in possible_paths:
            if os.path.exists(alt_path):
                print(f"  ✅ Found model at: {alt_path}")
                print(f"  💡 Update config.py to use this path")
                return False
        
        print("  ❌ Model not found in any common locations")
        print("\n📥 To download Llama-3.2-3B model:")
        print("  1. Visit: https://huggingface.co/meta-llama/Llama-3.2-3B")
        print("  2. Or use: huggingface-cli download meta-llama/Llama-3.2-3B")
        
        return False

def main():
    print("Llama-3.2-3B Model Checker")
    print("=" * 30)
    
    success = check_model_availability()
    
    if success:
        print("\n✅ Ready to run Smart Calendar with Llama-3.2-3B!")
    else:
        print("\n❌ Please ensure model is available before continuing")
        sys.exit(1)

if __name__ == "__main__":
    main()