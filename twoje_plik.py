from anthropic import Anthropic, HUMAN_PROMPT, ASSISTANT_PROMPT

# Zastąp "TwojeToken" swoim rzeczywistym tokenem API Claude
api_key = "TwojeToken"

client = Anthropic(api_key=api_key)

prompt = f"{HUMAN_PROMPT} Jak mogę Ci pomóc? {ASSISTANT_PROMPT}"
response = client.chat.completions.create(
    model="claude-2",
    prompt=prompt,
    max_tokens_to_sample=100
)

print(response.completion)
