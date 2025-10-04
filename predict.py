import requests
import pandas as pd
import numpy as np
import time
from pathlib import Path
import json
from datetime import datetime
import git
import logging

project_dir = Path(__file__).parent

def load_okrsek_results(url):
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data["vysledky"])
    df.columns=["KSTRANA", "NAZ_STRANA", "POC_HLASU", "OKRSEK_PRC"]
    return df

def git_push_results():
    """Add, commit, and push changes"""
    try:
        repo = git.Repo(project_dir)
        
        # Add only the specific file
        repo.index.add([project_dir / "docs" / "prubezne_vysledky.md"])

        # Commit
        repo.index.commit('Update prubezne vysledky')
        
        # Push
        origin = repo.remote(name='origin')
        origin.push()
        
        print("Successfully pushed to GitHub!")
    except Exception as e:
        print(f"Error: {e}")

mae_threshold = 2
results_2021 = pd.read_csv(project_dir / "results_2021.csv")

while True:
    intermediate_results = []
    for index, row in results_2021.iterrows():
        okrsek_result = load_okrsek_results(row["url_ps2025"])
        okrsek_result["PROP_MAE"] = row["PROP_MAE"]
        okrsek_result["WEIGHT"] = mae_threshold - okrsek_result["PROP_MAE"]
        intermediate_results.append(okrsek_result)
        time.sleep(1)
    inter_df = pd.concat(intermediate_results)
    to_publish = inter_df.groupby(["NAZ_STRANA"]).apply(lambda x: np.average(x["OKRSEK_PRC"], weights=x["WEIGHT"]))
    to_publish.name = "Procent hlasů"
    
    # Save to file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    with open(project_dir / "vysledky" / f"vysledky_report_{timestamp}.md", "w", encoding="utf-8") as f:
        f.write(f"# 🗳️ Volební výsledky podle strany:\n\nČas predikce:{timestamp}\n\n")
        f.write(to_publish.to_markdown())
    
    with open(project_dir / "docs" / f"prubezne_vysledky.md", "w", encoding="utf-8") as f:
        f.write(f"# 🗳️ Volební výsledky podle strany:\n\nČas predikce:{timestamp}\n\n")
        f.write(to_publish.to_markdown())

    git_push_results()
    time.sleep(30)

# visible at https://schubertjan.github.io/volby_2025/prubezne_vysledky