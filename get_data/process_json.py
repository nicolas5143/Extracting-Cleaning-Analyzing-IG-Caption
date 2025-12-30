import json
import csv
from datetime import datetime

# CONFIGURATION
INPUT_FILE = "instagram_auto_captured.json" # The file you just downloaded
OUTPUT_CSV = "final_competition_data.csv"

def extract_intercepted_data(file_path):
    print(f"📂 Processing {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            batches = json.load(f)
    except FileNotFoundError:
        print("❌ Error: File not found. Did you move the JSON file to this folder?")
        return

    all_posts = []
    seen_ids = set()

    # Iterate through every batch
    for batch in batches:
        
        # Recursive finder
        def find_posts(obj):
            if isinstance(obj, dict):
                timestamp = obj.get('taken_at') or obj.get('taken_at_timestamp')
                
                if timestamp:
                    code = obj.get('code') or obj.get('shortcode') or obj.get('pk')
                    
                    if code and str(code) not in seen_ids:
                        caption_text = ""
                        
                        # Extract Caption
                        if 'caption' in obj and isinstance(obj['caption'], dict):
                             caption_text = obj['caption'].get('text', '')
                        elif 'edge_media_to_caption' in obj:
                            edges = obj['edge_media_to_caption'].get('edges', [])
                            if edges:
                                caption_text = edges[0]['node']['text']
                        
                        seen_ids.add(str(code))
                        all_posts.append({
                            'date': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d'),
                            'url': f"https://instagram.com/p/{code}",
                            'caption': caption_text
                        })

                for key, value in obj.items():
                    find_posts(value)
            
            elif isinstance(obj, list):
                for item in obj:
                    find_posts(item)

        find_posts(batch)

    print(f"✅ Success! Extracted {len(all_posts)} unique posts.")
    
    if all_posts:
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'url', 'caption'])
            writer.writeheader()
            writer.writerows(all_posts)
        print(f"📊 Saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    extract_intercepted_data(INPUT_FILE)