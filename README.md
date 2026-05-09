# Bachelorarbeit: Ein systematischer Vergleich von Ansätzen zum Student Course Timetable Problem

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

**Autor:** Philipp Scheer  
**Betreuer:** Assoz.Prof PD Dr. Stefan Sobernig  
**Studium:** Wirtschafts- und Sozialwissenschaften, WU Wien  
**Abgabe:** Mai 2026

📄 [Thesis (PDF)](./thesis/Bachelorarbeit_Scheer_Signiert.pdf)


## Kurzfassung

Diese Bachelorarbeit ist eine konzeptionelle Replikationsstudie der Arbeit von
Feldman & Golumbic (1990), die zwei heuristische Algorithmen für das
*Single Student Scheduling Problem* (SSP) vorschlugen: **Hill-Climbing** und
**Offering-Order**. Da weder der originale Datensatz noch eine
Referenzimplementierung verfügbar sind, wurden die Algorithmen auf Basis des
Pseudocodes neu implementiert und anhand eines realen WU-Datensatzes evaluiert
(Hauptstudium Wirtschaftsinformatik, Sommersemester 2025, 381 Kurse, 28 Planpunkte).

Als zeitgemäße Baseline wurde ein **Integer Linear Programming (ILP)**-Ansatz
via CBC/Gurobi eingeführt, der dieselbe Rolle übernimmt wie Brute-Force in der
Ursprungsarbeit. Die Algorithmen wurden in **14 Szenarien** verglichen –
abgeleitet aus empirischen Studien zu studentischen Präferenzen sowie klassischen
Timetabling-Constraints.


## Wichtigste Ergebnisse

| Kriterium | Gewinner |
|---|---|
| Lösungsqualität (Mark) | Hill-Climbing v1 / v3 |
| Laufzeit | Offering-Order (schnellste Heuristik) |
| Laufzeit gesamt | **ILP (CPU)** – schneller als alle Heuristiken in fast allen Szenarien |

Moderne ILP-Solver übertreffen die Heuristiken
nicht nur in der Lösungsqualität, sondern in fast allen Szenarien auch in der
**Laufzeit** – womit der klassische Trade-off zwischen Exaktheit und
Geschwindigkeit für Probleminstanzen dieser Größenordnung nicht gilt.


## Algorithmen

- **Hill-Climbing v1** – wählt iterativ das Offering mit dem höchsten Zuwachs im Mark
- **Hill-Climbing v3** – wie v1, aber mit reduziertem Suchraum (zweite Hälfte der sortierten Offerings)
- **Offering-Order** – heuristische Sortierung mit Forward-Checking-Backtracking
- **ILP (CPU)** – exakte Lösung via PuLP/CBC
- **ILP (GPU)** – CUDA-beschleunigte Variante (NVIDIA RTX A5000)


## Testumgebung

- **CPU:** AMD EPYC 9334
- **RAM:** 128 GB
- **GPU:** 2× NVIDIA RTX A5000 (24 GB VRAM), CUDA 12.4
- **OS:** Ubuntu/Debian via Proxmox (Kernel 6.8.12)
- **Benchmarking:** [benchexec](https://github.com/sosy-lab/benchexec) –
  10 s Zeitlimit, 1 Core, 50 Wiederholungen pro Konfiguration
