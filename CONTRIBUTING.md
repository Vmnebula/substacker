# Contributing to Substacker

Thank you for your interest in contributing to Substacker! As an open-source AI cost intelligence and FinOps platform, community contributions help make this project more robust and feature-rich.

---

## 📜 Code of Conduct

Please be respectful, constructive, and collaborative in all issues, discussions, and pull requests.

---

## 🛠️ Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/substacker.git
   cd substacker
   ```
3. **Set up virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install pytest black flake8
   ```

---

## 💡 What Can You Work On?

We welcome PRs in any of the following areas:
- **New Provider Adapters:** Ingestors for Mistral, Cohere, Bedrock, Ollama, DeepSeek.
- **Enhanced Visualizations:** Custom reporting, exports (PDF/CSV/Slack summaries).
- **FinOps Optimization Rules:** Automated suggestions for model downgrade or caching.
- **SDK Extensions:** Node.js, Go, or TypeScript SDK clients.
- **Documentation & Testing:** Expanding test cases and developer guides.

---

## 🧪 Testing & Code Standards

Before submitting a PR, ensure all tests pass and formatting is clean:

```bash
# Run test suite
pytest

# Format code
black .
```

---

## 🚀 Submitting a Pull Request

1. Create a descriptive branch: `git checkout -b feature/gemini-caching-rates`
2. Commit your changes: `git commit -m 'feat: add Gemini prompt caching cost support'`
3. Push to your fork: `git push origin feature/gemini-caching-rates`
4. Open a Pull Request on the main `Vmnebula/substacker` repository.

---

## 📄 Licensing

By contributing to Substacker, you agree that your contributions will be licensed under the **GNU General Public License v3.0 (GPLv3)**.
