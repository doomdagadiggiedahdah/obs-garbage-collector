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
        
        from datetime import datetime
        import re
        import os
        
        # Process first 5 segments in reverse order (last to first)
        segments_to_process = segments_to_extract[:5]
        processed_segments = []
        
        for segment_num in reversed(segments_to_process):
            segment = next((s for s in segments if s['number'] == segment_num), None)
            
            if segment and isinstance(segment['line_start'], int) and isinstance(segment['line_end'], int):
                # Get the full content of the segment
                segment_content = '\n'.join(lines[segment['line_start']-1:segment['line_end']])
                
                # Generate a name for the extracted segment
                naming_prompt = f"""Generate a concise, descriptive filename for the following note content. The filename should:
- Be suitable for an Obsidian note (no special characters except hyphens and spaces)
- Capture the main concept or insight
- Be between 3-8 words
- Use lowercase with hyphens instead of spaces

Content to name:
{segment_content}

Return ONLY the filename without .md extension (e.g., "state-space-representation" or "recursive-neural-networks")."""
                
                note_name = call_llm(naming_prompt, temperature=0.3)
                
                # Clean the note name to ensure it's filesystem-safe
                note_name = re.sub(r'[^\w\s-]', '', note_name).strip()
                note_name = re.sub(r'[-\s]+', '-', note_name).lower()
                
                # Check if file already exists and modify name if needed
                base_name = note_name
                counter = 1
                new_note_path = f"/home/mat/Obsidian/ZettleKasten/{note_name}.md"
                
                while os.path.exists(new_note_path):
                    note_name = f"{base_name}-{counter}"
                    new_note_path = f"/home/mat/Obsidian/ZettleKasten/{note_name}.md"
                    counter += 1
                
                new_note_content = f"""---
date_creation: {datetime.now().strftime("%Y-%m-%d")}
time_creation: {datetime.now().strftime("%H:%M:%S")}
tags:
---

{segment_content}
"""
                
                try:
                    with open(new_note_path, 'w', encoding='utf-8') as new_file:
                        new_file.write(new_note_content)
                    
                    # Add link to generated note in original file after the extracted segment
                    link_text = f"- sent to [[{note_name}]]"
                    
                    # Insert the link after the last line of the extracted segment
                    insert_line = segment['line_end']
                    lines.insert(insert_line, link_text)
                    
                    processed_segments.append({
                        'number': segment_num,
                        'description': segment['description'],
                        'lines': f"{segment['line_start']}-{segment['line_end']}",
                        'note_name': note_name
                    })
                    
                except Exception as e:
                    print(f"\n❌ ERROR: Failed to create new note {new_note_path}: {e}")
        
        # Write the updated content back to the original file
        if processed_segments:
            updated_content = '\n'.join(lines)
            with open(note_path, 'w', encoding='utf-8') as original_file:
                original_file.write(updated_content)
        
        # Display processed segments
        for segment in processed_segments:
            print(f"\n📝 MOVED Segment {segment['number']}: {segment['description']}")
            print(f"   Lines {segment['lines']}")
            print(f"   Created note: {segment['note_name']}.md")
    else:
        print("No segments recommended for extraction.")


