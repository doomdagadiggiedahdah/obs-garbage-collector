"""Obsidian Note Segmentation and Extraction Tool

This tool analyzes Obsidian notes, segments them into logical parts,
and extracts valuable segments into separate notes.
"""

import csv
import io
import os
import re
from datetime import datetime

from groq import Groq


# Configuration
NOTE_PATH = "/home/mat/Obsidian/ZettleKasten/recurrence and state-spaces.md"
VAULT_PATH = "/home/mat/Obsidian/ZettleKasten"
MAX_SEGMENTS_TO_PROCESS = 5


def call_llm(prompt, temperature=0.3, stream=False):
    """Make a call to the GPT-OSS model with the given prompt.
    
    Args:
        prompt (str): The prompt to send to the model
        temperature (float): Sampling temperature (0.0 to 1.0)
        stream (bool): Whether to stream the response
    
    Returns:
        str or generator: Response content or stream object
    """
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
        return completion
    else:
        return completion.choices[0].message.content.strip()


def read_note(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    lines = content.split('\n')
    return content, lines


def add_line_numbers(lines):
    return '\n'.join([f"{i+1:3d}: {line}" for i, line in enumerate(lines)])


def segment_note(content):
    """Segment a note into logical parts using LLM.
    
    Args:
        content (str): The note content with line numbers
    
    Returns:
        str: CSV response from LLM
    """
    prompt = f"""Analyze the following Obsidian note and break it into logical segments. Each segment should represent a distinct idea, concept, or topic.

Return your response as CSV with these columns: segment_number,line_start,line_end,description

Example format:
1,1,5,YAML frontmatter metadata
2,7,11,Groq performance notes
3,12,28,Project ideas and brainstorming

Here is the note with line numbers:

{content}

IMPORTANT: Return ONLY the CSV data (no headers, no additional text)."""
    
    return call_llm(prompt)


def decide_segments_to_extract(segments_csv, original_content):
    """Decide which segments should be extracted into separate notes.
    
    Args:
        segments_csv (str): CSV string containing segment information
        original_content (str): Original note content
    
    Returns:
        list: List of segment numbers to extract
    """
    prompt = f"""You are helping with knowledge management in an Obsidian vault. Below are segments from a note, along with the original content.

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
    
    extraction_decision = call_llm(prompt, temperature=0.2)
    
    if extraction_decision.lower().strip() == "none":
        return []
    
    try:
        numbers = re.findall(r'\d+', extraction_decision)
        return [int(num) for num in numbers]
    except Exception as e:
        print(f"WARNING: Could not parse extraction response: {extraction_decision}")
        print(f"Error: {e}")
        return []


def parse_segments_csv(segments_csv):
    """Parse the CSV response into a list of segment dictionaries.
    
    Args:
        segments_csv (str): CSV string from LLM
    
    Returns:
        list: List of segment dictionaries
    """
    segments = []
    
    try:
        csv_reader = csv.reader(io.StringIO(segments_csv))
        
        for row in csv_reader:
            if len(row) >= 4:
                segment_num = int(row[0]) if row[0].isdigit() else row[0]
                line_start = int(row[1]) if row[1].isdigit() else row[1]
                line_end = int(row[2]) if row[2].isdigit() else row[2]
                description = row[3]
                
                segments.append({
                    'number': segment_num,
                    'line_start': line_start,
                    'line_end': line_end,
                    'description': description
                })
            else:
                print(f"WARNING: Skipping malformed row: {row}")
                
    except Exception as e:
        print(f"ERROR: Failed to parse CSV: {e}")
        print("Raw response:")
        print(segments_csv)
    
    return segments


def generate_note_name(segment_content):
    prompt = f"""Generate a concise, descriptive filename for the following note content. The filename should:
- Be suitable for an Obsidian note (no special characters except hyphens and spaces)
- Capture the main concept or insight
- Be between 3-8 words
- Use lowercase with hyphens instead of spaces

Content to name:
{segment_content}

Return ONLY the filename without .md extension (e.g., "state-space-representation" or "recursive-neural-networks")."""
    
    note_name = call_llm(prompt)
    
    # Clean the note name to ensure it's filesystem-safe
    note_name = re.sub(r'[^\w\s-]', '', note_name).strip()
    note_name = re.sub(r'[-\s]+', '-', note_name).lower()
    
    return note_name


def get_unique_filename(base_name, vault_path):
    """Get a unique filename by appending numbers if necessary.
    
    Args:
        base_name (str): Base filename without extension
        vault_path (str): Path to the vault directory
    
    Returns:
        tuple: (unique_name, full_path)
    """
    counter = 1
    note_name = base_name
    note_path = os.path.join(vault_path, f"{note_name}.md")
    
    while os.path.exists(note_path):
        note_name = f"{base_name}-{counter}"
        note_path = os.path.join(vault_path, f"{note_name}.md")
        counter += 1
    
    return note_name, note_path


def create_new_note(segment_content, note_path):
    """Create a new Obsidian note with metadata.
    
    Args:
        segment_content (str): Content for the new note
        note_path (str): Full path for the new note file
    
    Returns:
        bool: Success status
    """
    now = datetime.now()
    content = f"""---
date_creation: {now.strftime("%Y-%m-%d")}
time_creation: {now.strftime("%H:%M:%S")}
tags:
---

{segment_content}
"""
    
    try:
        with open(note_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return True
    except Exception as e:
        print(f"❌ ERROR: Failed to create new note {note_path}: {e}")
        return False


def process_segments(segments, segments_to_extract, lines, vault_path):
    """Process and extract selected segments into new notes.
    
    Args:
        segments (list): All parsed segments
        segments_to_extract (list): Segment numbers to extract
        lines (list): Original note lines
        vault_path (str): Path to the vault directory
    
    Returns:
        list: List of processed segment information
    """
    segments_to_process = segments_to_extract[:MAX_SEGMENTS_TO_PROCESS]
    processed_segments = []
    
    # Process segments in reverse order (last to first) to maintain line numbers
    for segment_num in reversed(segments_to_process):
        segment = next((s for s in segments if s['number'] == segment_num), None)
        
        if not segment:
            print(f"WARNING: Segment {segment_num} not found")
            continue
            
        if not (isinstance(segment['line_start'], int) and isinstance(segment['line_end'], int)):
            print(f"WARNING: Invalid line numbers for segment {segment_num}")
            continue
        
        # Extract segment content
        segment_content = '\n'.join(lines[segment['line_start']-1:segment['line_end']])
        
        # Generate note name and path
        base_name = generate_note_name(segment_content)
        note_name, note_path = get_unique_filename(base_name, vault_path)
        
        # Create the new note
        if create_new_note(segment_content, note_path):
            # Add link to original note
            link_text = f"- sent to [[{note_name}]]"
            lines.insert(segment['line_end'], link_text)
            
            processed_segments.append({
                'number': segment_num,
                'description': segment['description'],
                'lines': f"{segment['line_start']}-{segment['line_end']}",
                'note_name': note_name
            })
    
    return processed_segments


def update_original_note(note_path, lines):
    """Write updated content back to the original note.
    
    Args:
        note_path (str): Path to the original note
        lines (list): Updated lines
    
    Returns:
        bool: Success status
    """
    try:
        updated_content = '\n'.join(lines)
        with open(note_path, 'w', encoding='utf-8') as file:
            file.write(updated_content)
        return True
    except Exception as e:
        print(f"ERROR: Failed to update original note: {e}")
        return False


def print_results(processed_segments):
    """Print summary of processed segments.
    
    Args:
        processed_segments (list): List of processed segment information
    """
    for segment in processed_segments:
        print(f"\n📝 MOVED Segment {segment['number']}: {segment['description']}")
        print(f"   Lines {segment['lines']}")
        print(f"   Created note: {segment['note_name']}.md")


def main():
    """Main function to orchestrate the note segmentation and extraction process."""
    print("🔍 Starting note analysis...")
    
    # Read the note
    try:
        note_content, lines = read_note(NOTE_PATH)
    except FileNotFoundError:
        print(f"ERROR: Note not found at {NOTE_PATH}")
        return
    except Exception as e:
        print(f"ERROR: Failed to read note: {e}")
        return
    
    # Add line numbers and segment the note
    numbered_content = add_line_numbers(lines)
    segmentation_csv = segment_note(numbered_content)
    
    # Display segmentation results
    print("\n" + "=" * 50)
    print("SEGMENTATION CSV:")
    print("=" * 50)
    print(segmentation_csv)
    print("\n" + "=" * 50)
    
    # Parse segments
    segments = parse_segments_csv(segmentation_csv)
    
    if not segments:
        print("No segments found. Exiting.")
        return
    
    # Decide which segments to extract
    print("\n🤔 Analyzing segments for extraction...")
    segments_to_extract = decide_segments_to_extract(segmentation_csv, note_content)
    
    print("\n" + "=" * 50)
    print("EXTRACTION DECISION:")
    print("=" * 50)
    
    if segments_to_extract:
        print(f"Segments recommended for extraction: {segments_to_extract}")
        
        # Process segments
        processed_segments = process_segments(
            segments, segments_to_extract, lines, VAULT_PATH
        )
        
        # Update original note if any segments were processed
        if processed_segments:
            if update_original_note(NOTE_PATH, lines):
                print("\n✅ Original note updated successfully")
            
            print("\n" + "=" * 30)
            print("PROCESSING SUMMARY:")
            print("=" * 30)
            print_results(processed_segments)
        else:
            print("\n❌ No segments were successfully processed.")
    else:
        print("No segments recommended for extraction.")
    
    print("\n🎉 Analysis complete!")


if __name__ == "__main__":
    main()

