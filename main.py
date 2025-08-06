from groq import Groq
import csv
import io

# Read the Obsidian Zettelkasten note
note_path = "/home/mat/Obsidian/ZettleKasten/gpt-oss - hackathon.md"

with open(note_path, 'r', encoding='utf-8') as file:
    note_content = file.read()

# Add line numbers to the content for reference
lines = note_content.split('\n')
numbered_content = '\n'.join([f"{i+1:3d}: {line}" for i, line in enumerate(lines)])

client = Groq()
completion = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
      {
        "role": "user",
        "content": f"""Analyze the following Obsidian note and break it into logical segments. Each segment should represent a distinct idea, concept, or topic.

Return your response as CSV with these columns: segment_number,line_start,line_end,description

Example format:
1,1,5,YAML frontmatter metadata
2,7,11,Groq performance notes
3,12,28,Project ideas and brainstorming

Here is the note with line numbers:

{numbered_content}

IMPORTANT: Return ONLY the CSV data (no headers, no additional text)."""
      }
    ],
    temperature=0.3,
    max_completion_tokens=8192,
    top_p=1,
    reasoning_effort="medium",
    stream=False,
    stop=None
)

# Get the response
response_content = completion.choices[0].message.content.strip()

print(f"Reading note from: {note_path}\n")
print("=" * 50)
print("ORIGINAL NOTE CONTENT:")
print("=" * 50)
print(note_content)
print("\n" + "=" * 50)
print("AI RESPONSE (CSV):")
print("=" * 50)
print(response_content)
print("\n" + "=" * 50)

# Parse the CSV response
try:
    csv_reader = csv.reader(io.StringIO(response_content))
    
    print("PARSED SEGMENTS:")
    print("=" * 50)
    
    for row in csv_reader:
        if len(row) >= 4:  # Ensure we have all required columns
            segment_num = row[0]
            line_start = int(row[1]) if row[1].isdigit() else row[1]
            line_end = int(row[2]) if row[2].isdigit() else row[2]
            description = row[3]
            
            print(f"Segment {segment_num}: {description}")
            print(f"  Lines {line_start}-{line_end}")
            
            # Show the actual content for this segment
            if isinstance(line_start, int) and isinstance(line_end, int):
                segment_lines = lines[line_start-1:line_end]
                print(f"  Content: {segment_lines[0][:60]}..." if segment_lines else "  Content: [empty]")
            print()
        else:
            print(f"WARNING: Skipping malformed row: {row}")
            
except Exception as e:
    print(f"ERROR: Failed to parse CSV: {e}")
    print("Raw response:")
    print(response_content)

