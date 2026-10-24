from dotenv import load_dotenv
import anthropic

load_dotenv()                      # reads .env and sets ANTHROPIC_API_KEY
client = anthropic.Anthropic()     # finds the key automatically

response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=1000,
    messages=[{"role": "user", "content": "In one sentence: what is Hacker News?"}],
)

for block in response.content:
    if block.type == "text":
        print(block.text)

print("Tokens in:", response.usage.input_tokens, "| out:", response.usage.output_tokens)
