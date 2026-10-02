"""
Basic usage example for LocalAI Accelerator
"""

from local_ai_accelerator import LocalAIAccelerator


def main():
    print("=" * 70)
    print("LocalAI Accelerator - Basic Usage Example")
    print("=" * 70)
    
    # Initialize accelerator
    print("\n1️⃣  Initializing LocalAI Accelerator...")
    with LocalAIAccelerator() as accelerator:
        
        # Show system info
        print("\n2️⃣  System Specifications:")
        accelerator.print_system_info()
        
        # Show available models
        print("\n3️⃣  Available Models:")
        accelerator.print_available_models()
        
        # Get recommendations
        print("\n4️⃣  Recommended Model:")
        recommended = accelerator.recommend_model()
        print(f"   {recommended}")
        
        # Load a model
        print(f"\n5️⃣  Loading {recommended}...")
        if accelerator.load_model(recommended):
            print(f"   ✅ {recommended} loaded successfully")
        
        # Run inference
        print("\n6️⃣  Running Inference...")
        prompts = [
            "What is artificial intelligence?",
            "Explain machine learning in simple terms",
            "How do neural networks work?"
        ]
        
        for prompt in prompts:
            print(f"\n   Prompt: {prompt}")
            response = accelerator.inference(
                prompt=prompt,
                model_name=recommended,
                max_tokens=100
            )
            print(f"   Response: {response[:200]}...")
        
        # Show resource stats
        print("\n7️⃣  Resource Statistics:")
        accelerator.print_resource_stats()
        
        # Show optimization report
        print("\n8️⃣  Optimization Report:")
        accelerator.print_optimization_report()
        
        print("\n✅ Example completed successfully!")


if __name__ == "__main__":
    main()
