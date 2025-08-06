from groq import Groq

# Read the Obsidian Zettelkasten note
note_path = "/home/mat/Obsidian/ZettleKasten/gpt-oss - hackathon.md"

with open(note_path, 'r', encoding='utf-8') as file:
    note_content = file.read()

client = Groq()
completion = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
      {
        "role": "user",
        "content": f"Take the following note and return conceptual segments with line numbers that delineate concepts from each other:\n\n{note_content}"
      }
    ],
    temperature=1,
    max_completion_tokens=8192,
    top_p=1,
    reasoning_effort="medium",
    stream=True,
    stop=None
)

print(f"Reading note from: {note_path}\n")
print("=" * 50)
print("ORIGINAL NOTE CONTENT:")
print("=" * 50)
print(note_content)
print("\n" + "=" * 50)
print("GPT-OSS SUMMARY:")
print("=" * 50)

for chunk in completion:
    print(chunk.choices[0].delta.content or "", end="")

