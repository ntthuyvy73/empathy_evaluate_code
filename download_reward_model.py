#!/usr/bin/env python3
"""
Script to download Skywork Reward Model from Hugging Face
Supports resume if download was interrupted
"""

import os
from huggingface_hub import snapshot_download

def download_reward_model():
    """Download Skywork-Reward-V2-Llama-3.1-8B model"""
    
    # Target directory - absolute path
    model_dir = r"h:\Vy\Paper\Empathy\Code\EmotionTrajectory\ETrajEval\ETrajEval\Models\Skywork-Reward-V2-Llama-3.1-8B"
    
    print("="*60)
    print("Downloading Skywork-Reward-V2-Llama-3.1-8B")
    print("="*60)
    print(f"Target directory: {model_dir}")
    print(f"Model size: ~16GB")
    print(f"This may take a while depending on your internet speed...")
    print("="*60)
    
    # Create Models directory if not exists
    os.makedirs(os.path.dirname(model_dir), exist_ok=True)
    
    try:
        # Download with resume support
        model_path = snapshot_download(
            repo_id="Skywork/Skywork-Reward-V2-Llama-3.1-8B",
            local_dir=model_dir,
            local_dir_use_symlinks=False,
            resume_download=True,  # Resume if interrupted
            ignore_patterns=["*.md", "*.txt"],  # Skip unnecessary files
        )
        
        print("\n" + "="*60)
        print("✓ Download completed successfully!")
        print("="*60)
        print(f"Model saved to: {model_path}")
        
        # Verify downloaded files
        print("\nVerifying downloaded files...")
        required_files = [
            "config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json"
        ]
        
        # Check for model weights (either .safetensors or .bin)
        model_files = []
        for file in os.listdir(model_path):
            if file.endswith('.safetensors') or file.endswith('.bin'):
                model_files.append(file)
                file_size = os.path.getsize(os.path.join(model_path, file))
                print(f"  ✓ {file} ({file_size / (1024**3):.2f} GB)")
        
        all_present = True
        for file in required_files:
            file_path = os.path.join(model_path, file)
            if os.path.exists(file_path):
                print(f"  ✓ {file}")
            else:
                print(f"  ✗ {file} - MISSING!")
                all_present = False
        
        if not model_files:
            print(f"  ✗ Model weights - MISSING!")
            all_present = False
        
        if all_present:
            print("\n✓ All required files are present!")
            print("\nYou can now use this model in your config.yaml:")
            print(f'  reward_model_path: "{model_path}"')
        else:
            print("\n⚠ Some files are missing. Try running the script again.")
        
        return model_path
        
    except Exception as e:
        print(f"\n✗ Error downloading model: {e}")
        print("\nTroubleshooting:")
        print("1. Check your internet connection")
        print("2. Make sure you have enough disk space (~20GB free)")
        print("3. Install huggingface_hub: pip install huggingface_hub")
        print("4. Try running the script again (it will resume from where it stopped)")
        return None

if __name__ == "__main__":
    download_reward_model()
