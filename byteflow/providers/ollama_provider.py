class OllamaProvider:
    def __init__(self, model="llama3", num_predict=2048):
        """
        num_predict: max tokens Ollama will generate per response.
        Set generously (not left at whatever the model's own default
        is, which can be quite small for some models/configs) because
        a cut-off response is worse than a slow one here - a truncated
        code-generation response missing its closing code fence was a
        real observed bug (see agent.py's code() method, which now
        also defends against this by validating syntax before
        executing, but avoiding the truncation in the first place is
        better than only catching it after the fact).
        """
        try:
            import ollama
        except ImportError as e:
            raise ImportError(
                "OllamaProvider requires the 'ollama' package. "
                "Install it with: pip install ollama"
            ) from e

        self._ollama = ollama
        self.model = model
        self.num_predict = num_predict

    def generate(self, prompt):
        response = self._ollama.chat(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            options={"num_predict": self.num_predict},
        )

        return response["message"]["content"]