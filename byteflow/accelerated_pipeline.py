from local_ai_accelerator import ByteFlowAcceleratorPipeline, ByteFlowConfig

# Config
config = ByteFlowConfig(
    use_accelerator=True,
    enable_paged_attention=True,
    enable_continuous_batching=True,
    enable_kernel_fusion=True,
    num_gpus=1,
    batch_size=32,
    max_tokens=512
)

# Pipeline
pipeline = ByteFlowAcceleratorPipeline(config)

# Leads
leads = [
    {"url": "https://company1.com", "name": "Company 1"},
    {"url": "https://company2.com", "name": "Company 2"},
]

# Process
results = pipeline.process_batch(leads)

# Results ko sahi tarike se dekho
print(f"\n✅ Processing Complete!")
print(f"📊 Leads processed: {len(results)}")

for i, result in enumerate(results, 1):
    print(f"\n  Lead {i}:")
    print(f"    URL: {result.get('url', 'N/A')}")
    print(f"    Status: {result.get('status', 'processed')}")
    if 'time' in result:
        print(f"    Time: {result['time']:.3f}s")