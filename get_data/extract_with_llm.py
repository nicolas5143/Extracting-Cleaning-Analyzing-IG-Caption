import pandas as pd
import json
import time
import os
import ast # For safely reading lists from strings
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from groq import Groq 
import numpy as np

# --- CONFIGURATION ---
load_dotenv(Path(r"../.env"))
API_KEY = os.environ.get('API_KEY')
# print(f'API_KEY: {API_KEY}') # Optional debug
INPUT_FILE = r"..\data\final_competition_data_1cleaned.csv"
OUTPUT_FILE = r"..\data\final_competition_data_enriched.csv"

client = Groq(api_key=API_KEY)
MODEL_NAME = "llama-3.1-8b-instant" 

# 🧠 1. THE SEED MEMORY
known_categories = {
    "Web Development", "UI/UX Design", "Competitive Programming", 
    "Data Science", "Cyber Security", "Mobile Development", 
    "Game Development", "Poster Design", "Business Case", 
    "Essay", "Photography", "Videography", 
    "Science Olympiad", "Religious Competition", "Non-IT Competition"
}

SYSTEM_PROMPT = """
You are a data extraction assistant. Output ONLY valid JSON.
If a value is not found, use null.
"""

USER_PROMPT_TEMPLATE = """
Extract details from this caption.

EXAMPLE INPUT:
"PORSENI 2025! 
Lomba IT: Web Design, UI/UX.
Lomba Umum: Baca Puisi, Matematika, Fisika, Adzan, dan Pidato."

EXAMPLE JSON OUTPUT:
{{
  "post_category": "COMPETITION",
  "comp_category": ["Web Development", "UI/UX Design", "Non-IT Competition", "Science Olympiad", "Religious Competition"],
  "organizer": null,
  "target_audience": ["Umum"],
  "min_team_size": 1,
  "max_team_size": 1,
  "registration_fee": 0
}}

CURRENT KNOWN CATEGORIES:
{existing_cats}

INSTRUCTIONS:
1. post_category: 
   - Only filled with value from ["COMPETITION", "WEBINAR", "GIVEAWAY", or "OTHER"].
   - Map to "OTHER" if the post is not a competition/webinar/giveaway (e.g. promo/bootcamp).
   - Map to "COMPETITION" IF phrases like "kompetisi", "lomba" exist.
2. comp_category: 
   - IF post_category is "GIVEAWAY" or "OTHER", return null.
   - Otherwise, extract a LIST of categories.
   - 🔴 CRITICAL: Check 'CURRENT KNOWN CATEGORIES' above.
   - IF matches a known category, USE THAT NAME EXACTLY.
   - Rules:
     - Math/Science -> "Science Olympiad".
     - Religious (Adzan/MTQ) -> "Religious Competition".
     - General Arts/Sports -> "Non-IT Competition".
3. organizer: Main University/Company only. Ignore "BEM", "Himpunan".
4. target_audience: 
   - List from ["SD", "SMP", "SMA", "Mahasiswa", "Umum"].
   - Rules: "Siswa"/"SMK" -> "SMA". "Professional"/"Publik" -> "Umum". Default to "Umum" if unsure.
5. min_team_size & max_team_size: Integers or null.
6. registration_fee: Integer (0 if free).

CAPTION TO PROCESS:
"{caption_text}"

REQUIRED JSON STRUCTURE:
{{
  "post_category": "...",
  "comp_category": ["..."],
  "organizer": "...",
  "target_audience": ["..."],
  "min_team_size": ...,
  "max_team_size": ...,
  "registration_fee": ...
}}
"""

DEFAULT_DATA = {
    "post_category": "Unclassified",
    "comp_category": [],
    "organizer": None,
    "target_audience": ["Umum"],
    "min_team_size": None,
    "max_team_size": None,
    "registration_fee": 0
}

def analyze_caption(text, index):
    if not isinstance(text, str) or len(text) < 10 or text.lower() == 'nan':
        return None

    # Limit memory size to avoid token overflow (keep top 100 most used or just all if small)
    cats_string = ", ".join(sorted(list(known_categories)))

    for attempt in range(3):
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
                temperature=0, 
                response_format={"type": "json_object"} 
            )
            return json.loads(completion.choices[0].message.content)

        except Exception as e:
            if "429" in str(e): 
                time.sleep(15) # Wait longer for rate limits
            else:
                # Only print error if it's NOT a rate limit
                # print(f'Index: {index} error: {e}')
                return DEFAULT_DATA.copy()
    
    return DEFAULT_DATA.copy()

def main():
    print(f"🚀 Loading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)
    
    # Cleaning
    df['clean_text'] = df['clean_text'].replace('nan', np.nan)
    df = df.dropna(subset=['clean_text'])
    
    # --- CHECKPOINT & RESUME LOGIC (UPDATED) ---
    processed_indices = set()
    results = []
    
    if os.path.exists(OUTPUT_FILE):
        print(f"🔄 Found existing output file. Checking for valid progress...")
        try:
            existing_df = pd.read_csv(OUTPUT_FILE)
            
            # 🔴 FIX 1: AUTO-CLEAN THE "ZOMBIE" ROWS
            # We only count a row as 'done' if 'original_index' is NOT empty (NaN).
            # Unprocessed rows from a 'left join' will have NaN here.
            valid_existing = existing_df.dropna(subset=['original_index'])
            
            if not valid_existing.empty:
                processed_indices = set(valid_existing['original_index'].astype(int).tolist())
                results = valid_existing.to_dict('records')
                print(f"   ✅ Successfully resumed {len(processed_indices)} valid rows.")
                print(f"   (Ignored {len(existing_df) - len(valid_existing)} empty/null rows from previous run)")
            
            # Reload Memory
            if 'comp_category' in existing_df.columns:
                for cat_str in existing_df['comp_category'].dropna():
                    try:
                        cat_list = ast.literal_eval(str(cat_str))
                        if isinstance(cat_list, list):
                            for c in cat_list:
                                known_categories.add(c)
                    except: pass
        except Exception as e:
            print(f"⚠️ Could not read existing file: {e}. Starting fresh.")
    
    print(f"⚡ Processing {len(df)-len(processed_indices)} rows...")
    
    save_counter = 0
    
    for index, row in tqdm(df.iterrows(), total=df.shape[0]):
        # Skip if already done
        if index in processed_indices:
            continue
            
        data = analyze_caption(row['clean_text'], index)
        
        if data:
            data['original_index'] = index
            results.append(data)
            
            # Update Memory
            new_cats = data.get('comp_category', [])
            if isinstance(new_cats, list):
                for cat in new_cats:
                    if cat and cat not in known_categories:
                        known_categories.add(cat)
        
        save_counter += 1
        if save_counter >= 50:
            # 🔴 FIX 2: SAVE ONLY WHAT IS DONE
            extracted_df = pd.DataFrame(results)
            
            # 1. Filter original DF to ONLY the rows we have processed
            # This prevents the file from filling up with 1000 empty rows
            df_subset = df.loc[df.index.isin(extracted_df['original_index'])]
            
            # 2. Clean Columns (Prevent _x, _y duplicates)
            cols_to_keep = list(DEFAULT_DATA.keys()) + ['original_index']
            cols_to_keep = [c for c in cols_to_keep if c in extracted_df.columns]
            extracted_df_clean = extracted_df[cols_to_keep]
            
            # 3. Merge ONLY the subset
            temp_final_df = df_subset.merge(extracted_df_clean, left_index=True, right_on='original_index', how='left')
            
            temp_final_df.to_csv(OUTPUT_FILE, index=False)
            save_counter = 0

    # Final Save (Apply Fix 2 here as well)
    if results:
        extracted_df = pd.DataFrame(results)
        
        # Filter original DF
        df_subset = df.loc[df.index.isin(extracted_df['original_index'])]
        
        # Clean Columns
        cols_to_keep = list(DEFAULT_DATA.keys()) + ['original_index']
        cols_to_keep = [c for c in cols_to_keep if c in extracted_df.columns]
        extracted_df_clean = extracted_df[cols_to_keep]
        
        final_df = df_subset.merge(extracted_df_clean, left_index=True, right_on='original_index', how='left')
        
        print("\n✅ Success! Final Category List in Memory:")
        print(sorted(list(known_categories)))
        
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"💾 Final data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()