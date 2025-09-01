import os
import re
import bs4
import tqdm
import typer
import pickle
import requests

import pandas as pd

from datetime import datetime
from pqdm.threads import pqdm

from loguru import logger
from bachelorarbeit.config import PROCESSED_DATA_DIR, RAW_DATA_DIR
from bachelorarbeit.dtypes import Offering


app = typer.Typer()

url = "https://vvz.wu.ac.at/cgi-bin/vvz.pl?C=S&LANG=DE&U=H&S=25S&LV=3&L2=S&L3=S&T=&L=&I=$lvid&JOIN=AND"


WINF_CBK = [
    ("jub", ("5105",)),  # Jahresabschluss und Unternehmensberichte
    ("gb", ("5107",)),  # Global Business
    ("winf", ("5106",)),  # Grundlagen der Wirtschaftsinformatik
    ("fbwl", ("5108",)),  # Funktionsübergreifende Betriebswirtschaftslehre - Prozesse und Entscheidungen
    ("mik", ("5056", "6056")),  # Mikroökonomik (6056 ist Angewandte Mikroökonomik)
    ("mak", ("5059", "6059")),  # Makroökonomik (6059 ist Internationale Makroökonomik)
    ("zuwi", ("5117",)),  # Zukunftsfähiges Wirtschaften: Vertiefung und Anwendung
    (
        "wpr",
        ("5109", "6021"),
    ),  # Wirtschaftsprivatrecht (6021 ist Wirtschaft im rechtlichen Kontext - Wirtschaftsprivatrecht I)
    ("m", ("6023",)),  # Mathematik
    ("s", ("6024",)),  # Statistik
    (
        "swa",
        ("5136", "6911"),
    ),  # Standards wissenschaftlichen Arbeitens und Zitierens (6911 ist Grundlagen wissenschaftlichen Arbeitens)
]

# Vorraussetzungen um Kurse aus dem Hauptstudium zu belegen:
# mind 20 ECTS aus dem CBK

WINF_HAUPTSTUDIUM = [
    ("blp", ("6012",)),  # Beschaffung, Logistik, Produktion
    ("dke", ("5155",)),  # Grundlagen und Methoden des Data und Knowledge Engineering
    ("adp", ("9485",)),  # Algorithmisches Denken und Programmierung
    ("rn", ("5158",)),  # Rechnernetzwerke und Datenübermittlung: Grundlagen und Sicherheit
    ("bis", ("5160",)),  # Design von betrieblichen Informationssystemen
    ("mgm", ("5161",)),  # Governance und Management von IT-Projekten
    ("fm", ("5162",)),  # Forschungsmethoden der Wirtschaftsinformatik
]


@app.command()
def main():
    if not os.path.isfile(RAW_DATA_DIR / "vvz.pkl"):
        logger.info("Downloading VVZ dataset...")
        result = pqdm(range(1, 10_000), fetch_vorlesung, n_jobs=8)
        logger.success("Processing dataset complete.")

        with open(RAW_DATA_DIR / "vvz.pkl", "wb") as f:
            pickle.dump(result, f)
        logger.success("Storing dataset complete.")
    else:
        with open(RAW_DATA_DIR / "vvz.pkl", "rb") as f:
            result = pickle.load(f)
        logger.success("Loading dataset complete.")

    if not os.path.exists(RAW_DATA_DIR / "vvz_model.pkl"):
        logger.info("Building VVZ model.")

        only_existing_courses = [v[1] for v in result if v[0] == True]
        planpunkte = {}

        for course in tqdm.tqdm(only_existing_courses):
            for planpunkt in course["planpunkte"]:
                if planpunkt["id"] in planpunkte:
                    continue

                planpunkte[planpunkt["id"]] = fetch_planpunkt(planpunkt["href"])

        vvzModel = pd.DataFrame(only_existing_courses)

        vvzModel["planpunktIds"] = vvzModel["planpunkte"].apply(
            lambda x: [p["id"] for p in x] if isinstance(x, list) else []
        )
        vvzModel["ects"] = vvzModel["planpunktIds"].apply(
            lambda x: next((planpunkte.get(str(id), -1) for id in x), -1) if x else -1
        )

        def find_groupid_for_planpunktids(planpunktIds):
            for pp in planpunktIds:
                for groupId, courseIds in [*WINF_CBK, *WINF_HAUPTSTUDIUM]:
                    if pp in courseIds:
                        return groupId
            return None

        vvzModel["groupId"] = vvzModel["planpunktIds"].apply(find_groupid_for_planpunktids)
        vvzModel = vvzModel.rename(columns={"id": "courseId"})

        vvzModel.to_pickle(RAW_DATA_DIR / "vvz_model.pkl")
        logger.success("Done building VVZ model.")
    else:
        logger.success("VVZ model already built.")

    if not os.path.exists(RAW_DATA_DIR / "offerings.pkl"):
        logger.success("Converting VVZ model to list of offerings")
        with open(RAW_DATA_DIR / "vvz_model.pkl", "rb") as f:
            with open(RAW_DATA_DIR / "offerings.pkl", "wb") as f2:
                all_offerings = pickle.load(f).to_dict(orient="records")
                all_offerings = [
                    Offering(courseId=o["courseId"], groupId=o["groupId"], dates=o["dates"], ects=o["ects"])
                    for o in all_offerings
                ]
                pickle.dump(all_offerings, f2)
    else:
        logger.success("Converted list of offerings already exists")


def get_planpunkt_id(planpunkt_url):
    try:
        return re.findall(r"P=([0-9]+);", planpunkt_url)[0]
    except Exception:
        return None


def extract_vorlesung(id: any, soup: bs4.BeautifulSoup):
    tables = soup.find_all("table")

    vvzInfo = {"id": id, "dates": [], "lvLeiter": None, "planpunkte": []}

    for table in tables:
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            for idx, cell in enumerate(cells):
                text = cell.text.strip()
                if text == "Planpunkte Bachelor" and idx + 1 < len(cells):
                    planpunkte_links = cells[idx + 1].find_all("a")
                    planpunkte = [
                        {"text": a.text.strip(), "href": a.get("href"), "id": get_planpunkt_id(a.get("href"))}
                        for a in planpunkte_links
                    ]
                    vvzInfo["planpunkte"] = planpunkte
                if text == "LV-Leiter/in" and idx + 1 < len(cells):
                    lv_leiter = cells[idx + 1].text.strip()
                    vvzInfo["lvLeiter"] = lv_leiter

        first_tr = table.find("tr")

        if first_tr:
            first_td = first_tr.find("td")
            if first_td and first_td.text.strip() == "Termine":
                for row in table.find_all("tr")[1:]:  # Skipping the header row
                    cells = row.find_all("td")

                    if len(cells) >= 5:
                        date_str = cells[1].text.strip()
                        date_obj = datetime.strptime(date_str, "%d.%m.%Y")

                        time_str = cells[2].text.strip().replace(" Uhr", "")
                        start_time_str, end_time_str = time_str.split("-")

                        start_time = datetime.strptime(
                            f"{date_obj.strftime('%d.%m.%Y')} {start_time_str.strip()}", "%d.%m.%Y %H:%M"
                        )
                        end_time = datetime.strptime(
                            f"{date_obj.strftime('%d.%m.%Y')} {end_time_str.strip()}", "%d.%m.%Y %H:%M"
                        )

                        info = cells[3].text.strip()

                        room_str = cells[4].text.strip()
                        room_match = re.match(r"([A-Za-z0-9.]+)", room_str)
                        room = room_match.group(1) if room_match else "Unknown"

                        vvzInfo["dates"].append({"start": start_time, "end": end_time, "room": room, "info": info})
    return vvzInfo


def fetch_vorlesung(id):
    current_url = url.replace("$lvid", str(id))
    try:
        page = requests.get(current_url)
        if page.status_code == 200:
            soup = bs4.BeautifulSoup(page.text, "html.parser")

            if "Keine Lehrveranstaltungen gefunden" in soup.get_text():
                return (None, id, None)
            else:
                return (True, extract_vorlesung(id, soup), None)
        else:
            return (False, id, None)
    except Exception as e:
        return (False, id, e)


def fetch_planpunkt(p_url):
    try:
        page = requests.get(f"https://vvz.wu.ac.at{p_url}")
        if page.status_code == 200:
            soup = bs4.BeautifulSoup(page.text, "html.parser")

            for span in soup.select("span"):
                res = re.findall(r"([0-9]+) ECTS", span.text)
                if len(res) == 1:
                    return int(res[0])

            return None
        else:
            return (False, id, "code!=200")
    except Exception as e:
        return (False, id, e)


if __name__ == "__main__":
    app()
