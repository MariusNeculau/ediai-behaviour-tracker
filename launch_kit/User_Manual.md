# EDI AI Behaviour Tracker — User Manual

**For school staff, SNAs, and therapists. No technical knowledge required.**

---

## Getting Started

Double-click **start_app.bat** (in this folder). The app opens automatically in your browser at `http://127.0.0.1:5000`. Keep the black command window open in the background — closing it stops the server.

> **Tip:** Bookmark `http://127.0.0.1:5000` in your browser so you can open it directly next time.

---

## How to Log a Behaviour Incident

1. Click **+ Log Incident** in the left sidebar.
2. Select the **child** from the dropdown. The class fills in automatically.
3. Check the **date and time** — they default to right now.
4. Choose the **Incident Type** (e.g. Crisis, Behavioural, Self-Injury).
5. Select the **Severity**: Low, Medium, or High.
6. Choose the **Trigger** (what caused it).
7. Write a short **description** of what happened.
8. Tick any **Interventions** that were used (Calm Space, Deep Pressure, etc.).
9. Choose the **Outcome** and the **Staff Member** present.
10. Click **Save Incident**.

The incident appears immediately on the Dashboard.

---

## How to Log a Seizure (Epileptic Crisis)

1. Follow steps 1–4 above, selecting **Crisis** as the Incident Type.
2. A new **Subtype** field appears — select **Epileptic Seizure**.
3. A pink **Seizure Details** section opens below. Fill in:
   - **Seizure Type** (e.g. Tonic-Clonic, Absence)
   - **Duration** (in seconds)
   - **Recovery Time** (in minutes)
   - **Position During Seizure** (Floor, Seated, etc.)
   - Tick **Protocol Followed**, **Emergency Services Called**, or **Medication Administered** as appropriate
   - If medication was given, enter the **Medication Name**
   - Write any **Post-ictal Notes** (how the child was afterwards)
4. Click **Save Incident** as normal.

> **All seizure records are viewable in the Seizure Log tab in the sidebar.**

---

## How to Edit Data After Saving

### Edit a Seizure Record

1. Find the incident on the **Dashboard** or in **Child Profiles** and click the row.
2. In the incident popup, click **Edit Seizure Details** (red button at the bottom).
3. Change any fields you need.
4. Click **Save Changes**.

### Edit a Child's Details (name, class, key worker)

1. Go to **Settings** in the left sidebar.
2. Find the child under **Students** and click **Edit**.
3. Make your changes and click **Save**.

### Edit a Therapy Session Result

1. Go to **Therapy Sessions** in the sidebar.
2. Click the **Sessions** sub-tab.
3. Find the session with status **Planned** and click **Complete**.
4. Enter the results (trials, accuracy, prompt level, notes).
5. Click **Mark as Completed**.

---

## How to Generate a Report

### Individual Child Report (PDF)

1. Click **Reports** in the left sidebar.
2. Under **Report Type**, select **Individual Child**.
3. Choose the **child** and the **time period** (This Week / This Month / This Term).
4. Click **Generate Report**.
5. The PDF is saved automatically to the **Rapoarte_Salvate** folder on your computer. It appears in the **Recent Reports** list below.

### Class Summary or Whole School Report

Same steps as above — just select **Class Summary** or **Whole School** as the Report Type.

---

## How to Print the Emergency Protocol Card

The Emergency Protocol Card is a single printable page per child showing their seizure history, key details, and the 7-step first-aid protocol.

1. Go to **Child Profiles** and click on the child's name.
2. Click the **Emergency Card** button (top right of the profile).
3. The card opens in a new browser tab.
4. Press **Ctrl + P** to print.

> **Keep a printed copy in the child's classroom and the school office.**

---

## How to Export Data to CSV

CSV files can be opened in Microsoft Excel for further analysis or archiving.

### Export All Incidents

1. Go to **Reports** in the sidebar.
2. Click **↧ Export All Incidents (CSV)**.
3. The file is saved to the **Rapoarte_Salvate** folder. It appears in Recent Reports.

### Export Seizure Log Only

1. Go to **Reports** in the sidebar.
2. Click **↧ Export Seizure Log (CSV)** (the red button).
3. The file is saved to the **Rapoarte_Salvate** folder.

> **The CSV file name includes today's date and time, so you can keep multiple exports.**

---

## How to View the Seizure Log

1. Click **Seizure Log** in the left sidebar.
2. You see all seizure incidents across the whole school, with colour coding:
   - **Red row** — emergency services were called
   - **Yellow row** — protocol was not followed
3. Use the dropdown at the top to filter by a specific child.
4. Click any row to open the full incident details.

---

## How to Use Therapy Sessions

### As a Supervisor (Setting Goals)

1. Go to **Therapy Sessions** → **Goals** tab.
2. Click **+ Add Goal**.
3. Choose the child, skill area, and describe the objective.
4. Optionally set a target criteria (e.g. "80% accuracy over 3 sessions").
5. Click **Save Goal**.
6. To plan a session, go to the **Sessions** tab and click **+ Plan Session**.

### As a Therapist (Recording Results)

1. Go to **Therapy Sessions** → **Sessions** tab.
2. Find a session with status **Planned** and click **Complete**.
3. Enter: who conducted it, date/time, total trials, correct trials, prompt level, and notes.
4. Click **Mark as Completed**.

---

## Frequently Asked Questions

**Q: Is the data safe?**
All data is saved only on this computer. Nothing is sent to the internet. The database file is at `instance\behaviour.db` inside the app folder.

**Q: What if I close the browser by mistake?**
Just open your browser again and go to `http://127.0.0.1:5000`. Your data is not lost — it is saved in the database, not in the browser.

**Q: Can two people use the app at the same time?**
Yes, as long as both computers are on the same school network and both point their browser to the server computer's address (ask your IT coordinator for the network address).

**Q: Where are my saved reports?**
In the **Rapoarte_Salvate** folder inside the app folder. You can copy these to a USB stick or email them.

**Q: What if the app doesn't start?**
Make sure the black command window is still open. If it closed, double-click **start_app.bat** again. If you see an error message, contact your EDI AI administrator.

---

*EDI AI Behaviour Tracker — built for Irish special education schools.*
