"""
Example: load OPENAI_API_KEY from .env-local and test latest nano + chat models.
Run from the python/ directory so .env-local is found.
Models: gpt-5-nano (latest nano), gpt-5.2 (latest flagship chat).
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(".env-local")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise SystemExit("OPENAI_API_KEY not set. Add it to .env-local or the environment.")

client = OpenAI(api_key=api_key)

TEST_PROMPT = "Reply in one short sentence: what is 2+2?"


def chat(model: str, label: str) -> None:
    print(f"\n--- {label} ({model}) ---")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": TEST_PROMPT}],
    )
    text = response.choices[0].message.content
    print(text.strip())


def main() -> None:
    print("Testing latest nano and chat models...")
    chat("gpt-5-nano", "Latest nano")
    chat("gpt-5.2", "Latest chat")
    print("\nDone.")


if __name__ == "__main__":
    main()
