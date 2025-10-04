import requests
import pandas as pd
import numpy as np
import time
from pathlib import Path
import json
from datetime import datetime
import git
import logging
from settings import mae_threshold

project_dir = Path(__file__).parent


def load_okrsek_results(url, headers):
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data["vysledky"]:
            df = pd.DataFrame(data["vysledky"])
            df.columns = ["KSTRANA", "Názek strany", "POC_HLASU", "OKRSEK_PRC"]
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Error loading URL {url}: {e}")
        return pd.DataFrame()


def git_push_results():
    """Add, commit, and push changes"""
    try:
        repo = git.Repo(project_dir)

        # Add only the specific file
        repo.index.add([project_dir / "docs" / "prubezne_vysledky.md"])

        # Commit
        repo.index.commit("Update prubezne vysledky")

        # Push
        origin = repo.remote(name="origin")
        origin.push()

        print("Successfully pushed to GitHub!")
    except Exception as e:
        print(f"Error: {e}")


headers = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "cs,en-US;q=0.9,en;q=0.8",
        "Referer": "https://www.volby.cz/pls/ps2021/ps2?xjazyk=CZ",
        "X-Requested-With": "XMLHttpRequest",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "cs,en-US;q=0.7,en;q=0.3",
    },
    {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "application/json",
    },
]

mae_threshold = 2
results_2021 = pd.read_csv(project_dir / "results_2021.csv")
intermediate_results_path = project_dir / "cache" / "intermediate_results.json"


while True:
    if intermediate_results_path.exists():
        with open(intermediate_results_path, "r") as f:
            intermediate_results = json.load(f)
            intermediate_results = [pd.DataFrame(intermediate_result) for intermediate_result in intermediate_results]
    else:
        intermediate_results = []
    hash_cashed = [intermediate_result["okrsek_hash"].unique()[0] for intermediate_result in intermediate_results]

    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    print(f"Processing data for {timestamp}")
    while len(hash_cashed) <= results_2021.shape[0]:
        print(f"Processing {len(hash_cashed)} / {results_2021.shape[0]} okresku")
        for index, row in results_2021.iterrows():
            okrsek_hash = str(row["OKRES"])+str(row["OBEC"])+str(row["OKRSEK"])
            if okrsek_hash not in hash_cashed:
                header = np.random.choice(headers, 1)[0]
                okrsek_result = load_okrsek_results(row["url_ps2025"], header)
                if okrsek_result.shape[0] > 0:
                    okrsek_result["PROP_MAE"] = row["PROP_MAE"]
                    okrsek_result["WEIGHT"] = mae_threshold - okrsek_result["PROP_MAE"]
                    okrsek_result["okrsek_hash"] = okrsek_hash
                    intermediate_results.append(okrsek_result)
                time.sleep(5)
        if intermediate_results:
            inter_df = pd.concat(intermediate_results)
            to_publish = inter_df.groupby(["Názek strany"]).apply(
                lambda x: np.round(np.average(x["OKRSEK_PRC"], weights=x["WEIGHT"]), 2)
            )
            prc_threshold = 1.0
            to_publish = to_publish.loc[to_publish > prc_threshold]
            to_publish.sort_values(inplace=True, ascending=False)
            to_publish.name = f"Procent hlasů (strany s více než {prc_threshold}%)"

            # Save to file
            with open(
                project_dir / "vysledky" / f"vysledky_report_{timestamp}.md",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(
                    f"# 🗳️ Predikce volebních výsledků:\n\nČas predikce:{timestamp}\n\n"
                )
                f.write(to_publish.to_markdown())

            with open(
                project_dir / "docs" / f"prubezne_vysledky.md", "w", encoding="utf-8"
            ) as f:
                f.write(
                    f"# 🗳️ Predikce volebních výsledků:\n\nČas predikce: {timestamp}\n\n"
                )
                f.write(to_publish.to_markdown())
            with open(intermediate_results_path, "w") as f:
                json.dump([intermediate_result.to_dict(orient="records") for intermediate_result in intermediate_results], f)
            git_push_results()

# visible at https://schubertjan.github.io/volby_2025/prubezne_vysledky
