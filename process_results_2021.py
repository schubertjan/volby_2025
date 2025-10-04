import json
from pathlib import Path

import numpy as np
import pandas as pd

from settings import mae_threshold


def PROP_MAE(y, pred, count):
    return np.round(np.average(np.abs(y - pred), weights=count), 2)


def mae(y, pred):
    return np.round(np.mean(np.abs(y - pred)), 2)


def create_url(elec_id, okres, obec, okrsek):
    okres = str(int(okres))
    obec = str(int(obec))
    okrsek = str(int(okrsek))
    return f"https://www.volby.cz/appdata/{elec_id}/vysled/okrsek/{okres}/{obec}_{okrsek}.json"


project_dir = Path(__file__).parent
okrsky_2021 = pd.read_csv(
    project_dir / "volby_okrsky_2021.csv",
    sep=",",
    usecols=["OKRES", "OBEC", "OKRSEK", "KSTRANA", "POC_HLASU"],
)

okrsky_2021["OKRSEK_POC_HLASU"] = okrsky_2021.groupby(["OKRES", "OBEC", "OKRSEK"])[
    "POC_HLASU"
].transform("sum")
okrsky_2021["OKRSEK_PRC"] = np.round(
    100 * okrsky_2021["POC_HLASU"] / okrsky_2021["OKRSEK_POC_HLASU"], 2
)

celkovy_vysledek = np.round(
    100
    * okrsky_2021.groupby(["KSTRANA"], as_index=True)["POC_HLASU"].sum()
    / okrsky_2021["POC_HLASU"].sum(),
    2,
).reset_index()
celkovy_vysledek.columns = ["KSTRANA", "CR_PRC"]
okrsky_2021 = pd.merge(okrsky_2021, celkovy_vysledek, on="KSTRANA", how="left")

okrsky_mae = (
    okrsky_2021.groupby(["OKRES", "OBEC", "OKRSEK"])
    .apply(lambda x: PROP_MAE(x["OKRSEK_PRC"], x["CR_PRC"], x["POC_HLASU"]))
    .reset_index()
)
okrsky_mae.columns = ["OKRES", "OBEC", "OKRSEK", "PROP_MAE"]
okrsky_2021 = pd.merge(
    okrsky_2021, okrsky_mae, on=["OKRES", "OBEC", "OKRSEK"], how="left"
)

results = okrsky_2021.sort_values(by=["PROP_MAE", "OKRSEK_POC_HLASU"], ascending=True)[
    ["OKRES", "OBEC", "OKRSEK", "PROP_MAE", "OKRSEK_POC_HLASU"]
].drop_duplicates()


# based on threshold
results = results.loc[results["PROP_MAE"] < mae_threshold, :]
# based on overall % of okrsek

results["url_ps2021"] = results.apply(
    lambda x: create_url("ps2021", x["OKRES"], x["OBEC"], x["OKRSEK"]), axis=1
)
results["url_ps2025"] = results.apply(
    lambda x: create_url("ps2025", x["OKRES"], x["OBEC"], x["OKRSEK"]), axis=1
)

with open(project_dir / "results_2021.json", "w") as f:
    json.dump(results.to_dict(orient="records"), f)
results.to_csv(project_dir / "results_2021.csv", index=False)
