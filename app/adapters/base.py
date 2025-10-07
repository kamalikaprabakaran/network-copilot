class BaseAdapter:
    def generate(self, prompt: str, model: str = None, max_tokens: int = 512, temperature: float = 0.0) -> str:
        raise NotImplementedError
