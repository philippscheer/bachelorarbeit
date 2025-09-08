# Bachelorarbeit – Student Scheduling Problem

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>


Dieses Repository enthält die Implementierung und Evaluation meiner Bachelorarbeit im Studiengang Wirtschaftsinformatik.
Das Thema ist das Student Scheduling Problem (SSP), also die Erstellung eines möglichst optimalen Studienplans für Studierende im Hauptstudium WINF.  
Ziel ist es, individuelle Präferenzen (Constraints) und studienorganisatorische Rahmenbedingungen (VVZ) so zu berücksichtigen, 
dass Studierende ihre Kurse effizient und ohne Konflikte planen können.

Im Rahmen der Arbeit wurden die Algorithmen und Constraints aus der Publikation 
"Optimization Algorithms for Student Scheduling via Constraint Satisfiability" von Feldman & Golumbic
aufgegriffen, in diesem Projekt implementiert und anschließend anhand von Benchmarks evaluiert (TODO).

Dadurch soll aufgezeigt werden, wie sich verschiedene Optimierungsansätze in Hinblick auf Qualität, Laufzeit und
Skalierbarkeit bei der Erstellung von Stunden- und Studienplänen verhalten.



## Algorithmen

In dieser Arbeit wurden zwei Heuristiken aus Feldman & Golumbic (1990), Optimization Algorithms for Student Scheduling via Constraint Satisfiability, implementiert und angepasst:

- Hill Climbing (v1)
- Offering Order (fixed)

Beide Verfahren verfolgen das Ziel, aus einer Menge von Kursangeboten (Offerings) einen Stundenplan zu konstruieren, der alle Constraints erfüllt und mit Blick auf die Prioritäten (Mark) eine möglichst hohe Punktzahl (Qualität) erreicht.


### Hill Climbing

#### Funktionsweise nach Feldman & Golumbic

Das Hill-Climbing-Verfahren erzeugt in jeder Iteration alle erreichbaren Nachfolgerzustände, die durch das Hinzufügen eines Kurses entstehen können.
Jeder Nachfolger wird mit einer Bewertungsfunktion (Mark) bewertet. 
Anschließend wird der Zustand mit der höchsten Bewertung ausgewählt und als neuer aktueller Zustand übernommen.
Dies wiederholt sich solange, bis ein gültiger Stundenplan gefunden ist, d. h. ein Zustand, der alle Constraints erfüllt

Varianten im Paper:

- Version 1: Betrachtet alle möglichen Kurse als Erweiterung.
- Version 2 und 3: Einschränkungen auf Teilmengen zur Reduktion der Komplexität.


#### Anpassungen in meiner Implementierung

- Keine Gruppen: Das Paper unterscheidet zwischen Gruppen, Kursen und Offerings. In meiner Implementierung gibt es nur eine Ebene – direkt die Offerings. Dadurch entfällt die Auswahl von Gruppe und Kurs, ich wähle direkt das beste Offering.

- Abbruchbedingung: Das Paper stoppt, sobald ein gültiger Plan gefunden wurde. In meiner Implementierung kann der Algorithmus weiterlaufen, wenn ein zusätzliches Offering den Plan verbessert, solange die Maximalanzahl an Kursen nicht überschritten wird.


### Offering Order

#### Funktionsweise nach Feldman & Golumbic

Der Offering-Order-Ansatz basiert auf einer Sortierung:
1. Jedes Offering wird anhand einer Bewertungsfunktion markiert ("Mark").
2. Innerhalb eines Kurses (entspricht einem Planpunkt) werden die Offerings nach dieser Bewertung sortiert.
3. Kurse innerhalb einer Gruppe werden nach dem besten Offering sortiert.
Die Generierung des Stundenplans erfolgt dann per Forward Checking mit Backtracking: Nach jeder Auswahl wird geprüft, ob der teilweise Plan gültig bleibt.

Varianten im Paper:

- Preprocess Marking: Alle Bewertungen werden vorab berechnet und bleiben fix.
- Update Marks: Bewertungen werden nach jeder Kursauswahl neu angepasst.

#### Anpassungen in meiner Implementierung

- Gruppenbildung: Die Offerings werden anhand ihrer `groupId` in Gruppen eingeteilt (analog zum Paper).
- Sortierung: Ich nutze die „Preprocess Marking“-Variante (Marks werden nur einmal vorab berechnet und nicht aktualisiert, da ein nachträgliches Updaten der "Marks" diese nicht verändert).
- Backtracking: Implementiert als rekursiver Forward-Checking-Backtracking-Algorithmus.
- Kursanzahl-Constraint: Wird explizit berücksichtigt, sodass nur Pläne innerhalb der Min-/Max-Grenzen als gültig akzeptiert werden.



### Constraints

Die Qualität und Gültigkeit eines Stundenplans wird durch verschiedene Constraints bestimmt. In meiner Implementierung sind folgende Constraints umgesetzt:

- Feste Zeitfenster:
    Jede Stunde im Wochenplan kann mit einer Priorität von -100 bis +100 versehen werden.
    -100 = blockiert (keine Veranstaltungen erlaubt)
    +100 = Pflicht (Veranstaltung muss in diesem Zeitfenster stattfinden)
- Kurs-Prioritäten:
    Jedem Kurs (bzw. Planpunkt) kann eine Priorität zugeordnet werden (-100 bis +100). Dies erlaubt eine Gewichtung, ob ein Kurs bevorzugt oder vermieden werden soll.
- Hour Load Constraint:
    Minimal- und Maximalanzahl an Wochenstunden. Dadurch wird verhindert, dass ein Plan zu wenige oder zu viele Stunden enthält.
- Kursanzahl-Constraint:
    Minimal- und Maximalanzahl an belegten Kursen. Ein Stundenplan gilt nur dann als gültig, wenn er innerhalb dieser Grenzen liegt.

Constraints aus dem Paper, die ich nicht verwende:
- Unterscheidung zwischen Pflicht- und Wahlkursen über Gruppen:
    Im Paper werden strict groups und non-strict groups definiert.
    Diese Abbildung auf Pflicht- und Wahlkurse wird in meiner Implementierung nicht genutzt – stattdessen arbeite ich nur mit Offerings (Hill Climbing) bzw. Gruppen per groupId (Offering Order).

#### Nutzung in Experimenten

Die Algorithmen werden in verschiedenen Szenarien getestet, indem die Constraints verändert werden.
Dadurch lässt sich beobachten, wie robust Hill Climbing und Offering Order auf unterschiedliche Rahmenbedingungen reagieren – z. B. strikte vs. lockere Zeitrestriktionen, hohe vs. niedrige Prioritäten, enge vs. weite Stundenlast-Grenzen.


---


## Project Organization

```
├── LICENSE            <- Open-source license if one is chosen
├── Makefile           <- Makefile with convenience commands like `make data` or `make train`
├── README.md          <- The top-level README for developers using this project.
├── data
│   ├── external       <- Data from third party sources.
│   ├── interim        <- Intermediate data that has been transformed.
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── docs               <- A default mkdocs project; see www.mkdocs.org for details
│
├── models             <- Trained and serialized models, model predictions, or model summaries
│
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
│
├── pyproject.toml     <- Project configuration file with package metadata for 
│                         bachelorarbeit and configuration for tools like black
│
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
│
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
├── setup.cfg          <- Configuration file for flake8
│
└── bachelorarbeit   <- Source code for use in this project.
    │
    ├── __init__.py             <- Makes bachelorarbeit a Python module
    │
    ├── config.py               <- Store useful variables and configuration
    │
    ├── dataset.py              <- Scripts to download or generate data
    │
    ├── features.py             <- Code to create features for modeling
    │
    ├── modeling                
    │   ├── __init__.py 
    │   ├── predict.py          <- Code to run model inference with trained models          
    │   └── train.py            <- Code to train models
    │
    └── plots.py                <- Code to create visualizations
```

--------

