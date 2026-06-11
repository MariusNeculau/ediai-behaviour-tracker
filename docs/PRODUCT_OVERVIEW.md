# EDI AI — Behaviour Tracker
### Product Overview

**A self-contained desktop application for logging, analysing, and reporting student behaviour incidents in special-education settings.** Built in Ireland, for Irish schools.

---

## What it is

EDI AI Behaviour Tracker is a Windows desktop application that gives a school a single, private place to record behavioural incidents, manage students and staff, and produce professional reports — all without an internet connection, a server, or a software install. The entire system runs from one executable file and stores its data locally on the school's own machine.

## Who it's for

- **Special-education schools and units** that need a structured, GDPR-compliant record of behaviour incidents.
- **Teachers, SNAs, and key workers** logging day-to-day incidents and interventions.
- **School leadership** who need class-level and whole-school summaries for review meetings, planning, and oversight.

## Key features

| Capability | What it does |
|---|---|
| **Incident logging** | Record each incident with type, severity, trigger, interventions used, outcome, duration, and free-text notes. |
| **Student, staff & class management** | Full add / edit / archive for students, staff, and classrooms. Archiving (soft-delete) hides a record from active lists while **preserving its incident history** — nothing is ever lost. |
| **School settings** | Configure the school's name and roll number directly in the app; they appear on every report. |
| **Dashboard** | At-a-glance view of today's incidents, active crises, students monitored, recent incidents, and a time-of-day pattern chart. |
| **Professional PDF reports** | One-click generation of three report types: **Individual Child** (student details, key statistics, full incident log, and an aggregated pattern analysis of triggers, behaviours, and actions taken), **Class Summary**, and **Whole School** — each with a per-student or per-class breakdown and an official page footer. |
| **CSV data export** | Export every incident to a spreadsheet-ready CSV (UTF-8) for the school's own analysis or archiving. |
| **Automatic pattern analysis** | Reports automatically summarise the most frequent triggers, behaviour types, peak times of day, and key statistics (totals, weekly averages, typical severity and duration) from the logged data. |

## How it works

1. **Download** a single `.exe` file from the releases page — no Python, no installer, no admin rights required.
2. **Run it** — the application opens in the staff member's web browser; the interface looks and feels like a modern web app but runs entirely on the local machine.
3. **Data stays local** — all records are saved in a database file kept next to the application, on the school's own computer. Nothing is transmitted to external servers.

## Data privacy & compliance

- **Local-only storage.** No personal data leaves the school's premises or device.
- **GDPR-aligned** and consistent with the **Irish Data Protection Act 2018**.
- Records are accessible only to staff with access to the school's machine.

## Technical summary

- **Platform:** Windows desktop (single-file executable).
- **Architecture:** Flask web application with a SQLite database, packaged with PyInstaller.
- **Reports:** generated natively as PDF; data export as CSV.
- **Footprint:** ~30 MB; no external dependencies or network access needed at runtime.

## Getting started

Download the latest Windows application from the
**[releases page](https://github.com/MariusNeculau/ediai-behaviour-tracker/releases/latest)**,
place the `.exe` in its own folder, and double-click to launch.

---

**Contact**
Marius Neculau — AI Engineer — Galway, Ireland
mariusneculau@gmail.com
