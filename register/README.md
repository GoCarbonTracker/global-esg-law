# Register

`register.csv` maps jurisdictions and instruments in the pilot corpus. It was seeded once with `tools/seed_register.py <path-to-merged-csv>`; the pilot rows (EU, GB, IN, US) have since been edited per instrument. `tools/seed_register.py` refuses to run while `register.csv` exists, because rerunning it would drop those rows.
