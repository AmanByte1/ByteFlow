class OllamaProvider:
    def __init__(self, model="llama3"):
        try:
            import ollama
        except ImportError as e:
            raise ImportError(
                "OllamaProvider requires the 'ollama' package. "
                "Install it with: pip install ollama"
            ) from e

        self._ollama = ollama
        self.model = model

    def generate(self, prompt):
        response = self._ollama.chat(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response["message"]["content"]