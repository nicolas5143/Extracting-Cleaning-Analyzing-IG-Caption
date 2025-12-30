import pandas as pd
import json
import time
import os
import ast
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from groq import Groq 
import numpy as np

# --- CONFIGURATION ---
load_dotenv(Path(r"../.env"))
API_KEY = os.environ.get('API_KEY')
DATA_FILE = r"..\data\final_competition_data_enriched.csv"

client = Groq(api_key=API_KEY)
# MODEL_NAME = "llama-3.1-8b-instant" 
MODEL_NAME = "openai/gpt-oss-20b"

# 🧠 1. SEED MEMORY
known_categories = {
    "Web Development", "UI/UX Design", "Competitive Programming", 
    "Data Science", "Cyber Security", "Mobile Development", 
    "Game Development", "Poster Design", "Science Olympiad", 
    "Religious Competition", "Non-IT Competition"
}

SYSTEM_PROMPT = "You are a data extraction assistant. Output ONLY valid JSON."

# 🧠 2. PROMPT WITH MEMORY (Re-added)
USER_PROMPT_TEMPLATE = """
Extract info from caption.

CURRENT KNOWN CATEGORIES:
{existing_cats}

INSTRUCTIONS:
1. post_category: ["COMPETITION", "WEBINAR", "GIVEAWAY", or "OTHER"].
2. comp_category: 
   - IF the category of the post is "GIVEAWAY" or "OTHER", map with a null value.
   - Match 'CURRENT KNOWN CATEGORIES' if possible. Map Math/Science->"Science Olympiad", Religious->"Religious Competition", Art/Speech->"Non-IT Competition".
3. organizer: Main University/Company only. Ignore "BEM", "Himpunan".
4. target_audience: 
   - List from ["SD", "SMP", "SMA", "Mahasiswa", "Umum"].
   - RULES:
     - IF "Siswa", "Pelajar", "SMK", "SLTA", "Sederajat" map to "SMA".
     - IF implies all ages/general/profesional -> map to "Umum".
5. min_team_size & max_team_size: Integer or null.
6. registration_fee:
   - Return list of integer incase theres number of registration batch, return [0] if none.
   - AVOID extracting from the phrase indicating the prize number.
   - ONLY extract registration fee as the numbers in the caption. If in dollar, in dollar ("$10" -> 10), applies in rupiah too. 

CAPTION TO PROCESS:
"{caption_text}"

REQUIRED JSON STRUCTURE:
{{
  "post_category": "COMPETITION, WEBINAR, GIVEAWAY, or OTHER",
  "comp_category": ["..."],
  "organizer": "...",
  "target_audience": ["..."],
  "min_team_size": ...,
  "max_team_size": ...,
  "registration_fee": [...]
}}
"""

def analyze_caption(text):
    if not isinstance(text, str) or len(text) < 10: return None

    # Create the memory string, filter out None values to prevent the crash
    clean_cats = [c for c in known_categories if c is not None and isinstance(c, str)]
    cats_string = ", ".join(sorted(clean_cats))

    for attempt in range(5):
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                        existing_cats=cats_string, 
                        caption_text=text
                    )}
                ],
                temperature=0, response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)

        except Exception as e:
            error_msg = str(e).lower()
            
            # 🛑 KILL SWITCH (Daily Limit)
            if "quota" in error_msg or ("limit" in error_msg and "0" in error_msg):
                print(f"\n❌ DAILY LIMIT REACHED! Stopping script immediately.")
                return "STOP_SIGNAL"

            # ⚠️ SPEED BUMP (Rate Limit)
            if "429" in error_msg:
                wait = 20 + (attempt * 10)
                print(f"⏳ Speed Limit Hit. Sleeping {wait}s...")
                time.sleep(wait)
            else:
                return None 
                
    return None

def main():
    print(f"🚀 Loading {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE)
    
    # 🧠 PRE-LEARNING: Scan the 'Good' rows to relearn categories
    print("🧠 Re-learning existing categories from successful rows...")
    good_rows = df[df['post_category'] != 'Unclassified']
    if 'comp_category' in good_rows.columns:
        for cat_str in good_rows['comp_category'].dropna():
            try:
                # Parse string "['Web', 'UI']" -> list
                cat_list = ast.literal_eval(str(cat_str))
                if isinstance(cat_list, list):
                    if c and isinstance(c, str): 
                        for c in cat_list: known_categories.add(c)
            except: pass
    print(f"✅ Loaded {len(known_categories)} categories into memory.")

    # Identify failures
    failed_indices = df[df['post_category'] == 'Unclassified'].index.tolist()
    print(f"📉 Found {len(failed_indices)} unclassified rows to repair.")
    
    if not failed_indices:
        print("✅ Nothing to repair!")
        return

    print(f"⚡ Starting Smart Repair...")
    save_counter = 0
    
    for idx in tqdm(failed_indices):
        text = str(df.loc[idx, 'clean_text'])
        
        if text.lower() == 'nan' or len(text) < 10:
            continue

        data = analyze_caption(text)
        
        # 🛑 KILL SWITCH
        if data == "STOP_SIGNAL":
            print("💾 Saving and exiting...")
            df.to_csv(DATA_FILE, index=False)
            return 

        if data:
            for key, value in data.items():
                if key in df.columns:
                    df.at[idx, key] = value
            
            # Update Memory Dynamically
            if isinstance(data.get('comp_category'), list):
                for c in data['comp_category']: known_categories.add(c)
        
        save_counter += 1
        if save_counter >= 10:
            df.to_csv(DATA_FILE, index=False)
            save_counter = 0
            
        time.sleep(1) 

    df.to_csv(DATA_FILE, index=False)
    print(f"✅ Repairs Complete!")

if __name__ == "__main__":
    main()