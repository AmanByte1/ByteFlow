from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="localai-accelerator",
    version="1.0.0",
    author="LocalAI Community",
    description="Optimize local AI model inference with intelligent CPU/GPU management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/localai-community/localai-accelerator",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "psutil>=5.9.0",
        "pynvml>=12.0.0",
        "torch>=2.0.0",
        "numpy>=1.21.0",
        "pydantic>=2.0.0",
        "aioqueue>=0.2.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
        "llama": ["llama-cpp-python>=0.2.0"],
        "transformers": ["transformers>=4.30.0", "bitsandbytes>=0.40.0"],
        "ollama": ["ollama>=0.1.0"],
    },
)
