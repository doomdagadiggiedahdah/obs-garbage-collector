from groq import Groq
import csv
import io

def call_llm(prompt, temperature=0.3, stream=False):
    """Make a call to the GPT-OSS model with the given prompt"""
    client = Groq()
    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
          {
            "role": "user",
            "content": prompt
          }
        ],
        temperature=temperature,
        max_completion_tokens=8192,
        top_p=1,
        reasoning_effort="medium",
        stream=stream,
        stop=None
    )
    
    if stream:
        return completion  # Return the stream object for streaming responses
    else:
        return completion.choices[0].message.content.strip()

# Read the Obsidian Zettelkasten note
note_path = "/home/mat/Obsidian/ZettleKasten/recurrence and state-spaces.md"
append_path = "/home/mat/Obsidian/ZettleKasten/gpt-oss - append here.md"

with open(note_path, 'r', encoding='utf-8') as file:
    note_content = file.read()

# Add line numbers to the content for reference
lines = note_content.split('\n')
numbered_content = '\n'.join([f"{i+1:3d}: {line}" for i, line in enumerate(lines)])

# Define the segmentation prompt
segmentation_prompt = f"""Analyze the following Obsidian note and break it into logical segments. Each segment should represent a distinct idea, concept, or topic.

Return your response as CSV with these columns: segment_number,line_start,line_end,description

Example format:
1,1,5,YAML frontmatter metadata
2,7,11,Groq performance notes
3,12,28,Project ideas and brainstorming

Here is the note with line numbers:

{numbered_content}

IMPORTANT: Return ONLY the CSV data (no headers, no additional text)."""

# Get the segmentation response
segmentation_csv = call_llm(segmentation_prompt)

print(f"Reading note from: {note_path}\n")
print("=" * 50)
print(note_content)
print("\n" + "=" * 50)
print("SEGMENTATION CSV:")
print("=" * 50)
print(segmentation_csv)
print("\n" + "=" * 50)

def decide_segments_to_extract(segments_csv, original_content):
    """Decide which segments should be extracted into separate notes"""
    
    extraction_prompt = f"""You are helping with knowledge management in an Obsidian vault. Below are segments from a note, along with the original content.

Your task: Identify which segments should be extracted into separate notes. Extract segments that contain:
- Interesting insights or "aha" moments
- Solutions to problems you've struggled with
- Noteworthy concepts that deserve their own note
- Ideas with clear value that could be referenced later
- Complete thoughts that stand alone well

DO NOT extract:
- Metadata/frontmatter
- Simple lists without context
- Incomplete thoughts or rough brainstorming
- Administrative notes

Segments (CSV format: segment_number,line_start,line_end,description):
{segments_csv}

Original content:
{original_content}

Return ONLY the segment numbers to extract, comma-separated (e.g., "2,5,7" or "none" if nothing should be extracted)."""
    
    extraction_decision = call_llm(extraction_prompt, temperature=0.2)
    
    # Parse the response to get segment numbers
    if extraction_decision.lower().strip() == "none":
        return []
    
    try:
        # Extract numbers from response, handle various formats
        import re
        numbers = re.findall(r'\d+', extraction_decision)
        return [int(num) for num in numbers]
    except:
        print(f"WARNING: Could not parse extraction response: {extraction_decision}")
        return []

# Parse the CSV response
segments = []
try:
    csv_reader = csv.reader(io.StringIO(segmentation_csv))
    
    print("PARSED SEGMENTS:")
    print("=" * 50)
    
    for row in csv_reader:
        if len(row) >= 4:  # Ensure we have all required columns
            segment_num = int(row[0]) if row[0].isdigit() else row[0]
            line_start = int(row[1]) if row[1].isdigit() else row[1]
            line_end = int(row[2]) if row[2].isdigit() else row[2]
            description = row[3]
            
            segment_info = {
                'number': segment_num,
                'line_start': line_start,
                'line_end': line_end,
                'description': description
            }
            segments.append(segment_info)
            
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
    print(segmentation_csv)

# Decide which segments to extract
if segments:
    print("\n" + "=" * 50)
    print("EXTRACTION DECISION:")
    print("=" * 50)
    
    segments_to_extract = decide_segments_to_extract(segmentation_csv, note_content)
    
    if segments_to_extract:
        print(f"Segments recommended for extraction: {segments_to_extract}")
        
        # Append the first segment to the append file
        first_segment_num = segments_to_extract[0]
        first_segment = next((s for s in segments if s['number'] == first_segment_num), None)
        
        if first_segment and isinstance(first_segment['line_start'], int) and isinstance(first_segment['line_end'], int):
            # Get the full content of the first segment
            first_segment_content = '\n'.join(lines[first_segment['line_start']-1:first_segment['line_end']])
            
            # Create the append content with metadata
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            append_content = f"""

---
## Extracted Segment - {timestamp}
**Source:** {note_path}
**Description:** {first_segment['description']}
**Original Lines:** {first_segment['line_start']}-{first_segment['line_end']}

{first_segment_content}
"""
            
            # Append to the file
            try:
                with open(append_path, 'a', encoding='utf-8') as append_file:
                    append_file.write(append_content)
                print(f"\n✅ APPENDED first segment to: {append_path}")
                print(f"   Segment {first_segment_num}: {first_segment['description']}")
            except Exception as e:
                print(f"\n❌ ERROR: Failed to append to {append_path}: {e}")
        
        # Display all segments for review
        for segment_num in segments_to_extract:
            segment = next((s for s in segments if s['number'] == segment_num), None)
            if segment:
                print(f"\n📝 Extract Segment {segment_num}: {segment['description']}")
                print(f"   Lines {segment['line_start']}-{segment['line_end']}")
                
                # Show the full content of this segment
                if isinstance(segment['line_start'], int) and isinstance(segment['line_end'], int):
                    segment_content = '\n'.join(lines[segment['line_start']-1:segment['line_end']])
                    print(f"   Content preview: {segment_content[:200]}...")
    else:
        print("No segments recommended for extraction.")


