# Contributing to LocalAI Accelerator

Thank you for your interest in contributing! This guide will help you get started.

## 🎯 How You Can Contribute

- 🐛 Report bugs and issues
- ✨ Suggest new features
- 📝 Improve documentation
- 🔧 Fix bugs and implement features
- 🧪 Add tests and improve coverage
- 📊 Optimize performance
- 🌍 Add support for new models/frameworks

## 📋 Prerequisites

- Python 3.8+
- PyTorch knowledge (helpful)
- Git experience
- Local AI experience (helpful)

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then clone
git clone https://github.com/YOUR_USERNAME/localai-accelerator.git
cd localai-accelerator
git remote add upstream https://github.com/localai-community/localai-accelerator.git
```

### 2. Create Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install in development mode
pip install -e ".[dev,llama,transformers]"

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### 3. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number
```

## 📝 Development Guidelines

### Code Style

We use Black for formatting:

```bash
# Format code
black local_ai_accelerator/
black tests/

# Check formatting
flake8 local_ai_accelerator/

# Type checking
mypy local_ai_accelerator/
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_system_profiler.py

# With coverage
pytest --cov=local_ai_accelerator tests/
```

### Adding a Feature

```python
# 1. Write test first (TDD)
# tests/test_my_feature.py
def test_my_feature():
    assert my_feature() == expected

# 2. Implement feature
# local_ai_accelerator/my_feature.py

# 3. Add documentation
# docs/MY_FEATURE.md

# 4. Update README.md if needed
```

### Commit Messages

Follow conventional commits:

```bash
feat: add new feature
fix: resolve bug
docs: update documentation
test: add tests
perf: improve performance
refactor: reorganize code
```

Example:
```bash
git commit -m "feat: add vLLM integration"
git commit -m "fix: handle GPU memory edge cases"
```

## 🧪 Adding Tests

Test locations: `tests/test_*.py`

```python
import pytest
from local_ai_accelerator import LocalAIAccelerator


class TestLocalAIAccelerator:
    @pytest.fixture
    def accelerator(self):
        return LocalAIAccelerator()
    
    def test_initialization(self, accelerator):
        assert accelerator is not None
    
    def test_system_specs(self, accelerator):
        specs = accelerator.get_system_specs()
        assert 'cpu_cores' in specs
        assert 'gpu_available' in specs
    
    @pytest.mark.slow
    def test_inference(self, accelerator):
        accelerator.load_model("phi-2")
        response = accelerator.inference("Hello", "phi-2")
        assert len(response) > 0
```

Run tests:
```bash
# All tests
pytest tests/

# Specific test
pytest tests/test_accelerator.py::TestLocalAIAccelerator::test_initialization

# Skip slow tests
pytest -m "not slow" tests/

# Verbose output
pytest -v tests/
```

## 📖 Documentation

### Adding Documentation

1. Create markdown file in `docs/`
2. Use clear headings and examples
3. Include code examples
4. Add to table of contents

```markdown
# My Feature

## Overview
[Brief description]

## Usage
[Code examples]

## Configuration
[Config options]

## Troubleshooting
[Common issues]
```

### Updating README

Edit `README.md`:
- Add feature to features list
- Update examples if needed
- Update benchmarks if performance changed
- Update roadmap if applicable

## 🔍 Code Review Process

1. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request**
   - Clear title and description
   - Reference related issues (#123)
   - Describe changes and benefits

3. **Address Review Comments**
   - Make requested changes
   - Push updates
   - Reply to comments

4. **Merge**
   - Maintainers will merge when approved
   - Delete your feature branch

## 🐛 Reporting Bugs

Create a GitHub issue with:

```markdown
## Bug Description
[Clear description of the bug]

## Reproduction Steps
1. [First step]
2. [Second step]
3. ...

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- Python version: [e.g., 3.10]
- GPU: [e.g., RTX 4090]
- OS: [e.g., Ubuntu 22.04]

## Logs/Errors
[Paste error messages]

## Additional Context
[Any other relevant info]
```

## ✨ Suggesting Features

Create a GitHub discussion or issue:

```markdown
## Feature Request
[Description of desired feature]

## Motivation
Why would this be useful?

## Proposed Solution
How would it work?

## Alternatives
Any other approaches?

## Additional Context
[Any other details]
```

## 📊 Performance Contributions

Help us optimize!

1. **Profile code**
   ```python
   import cProfile
   cProfile.run('accelerator.inference(...)')
   ```

2. **Benchmark changes**
   ```bash
   python benchmarks/benchmark_inference.py
   ```

3. **Document improvements**
   - Include benchmark results
   - Explain optimization technique
   - Test on different hardware

## 🤝 Code of Conduct

- Be respectful and inclusive
- Welcome diverse perspectives
- Provide constructive feedback
- Help others learn

## 🎓 Learning Resources

- [PyTorch Documentation](https://pytorch.org/docs/)
- [vLLM](https://vllm.ai/) - Inspiration for request optimization
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - Efficient inference
- [Local LLMs Guide](https://github.com/jmorganca/ollama)

## ❓ Questions?

- Create a GitHub Discussion
- Open an issue for clarity
- Join community chat
- Email: [contact info]

## 🙏 Thank You

Your contributions make LocalAI Accelerator better for everyone! 

---

**Happy coding!** 🚀
