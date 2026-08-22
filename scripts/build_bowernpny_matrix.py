#!/usr/bin/env python3
import argparse
import csv
from collections import defaultdict
from pathlib import Path

# Pilot deliberately samples six varieties from each of the four major
# divisions described by Bowern & Atkinson (2012): Southeastern, Northern,
# Central, and Western.
LANGUAGES = {
    "Southeastern": [
        "Awabakal", "Bandjalang", "Gumbaynggir",
        "Wathawurrung", "Bunganditj", "Wiradjuri",
    ],
    "Northern": [
        "Kalkatungu", "Mayi-Kulan", "Dyirbal",
        "Guugu-Yimidhirr", "Yidiny", "Wik Mungkan",
    ],
    "Central": [
        "Adnyamathanha", "Arabana", "Diyari",
        "Paakantyi", "Wangkangurru", "Pitta-Pitta",
    ],
    "Western": [
        "Pitjantjatjara", "Ngaanyatjarra", "Warlpiri",
        "Warumungu", "Nyangumarta", "Yindjibarndi",
    ],
}

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_phylip(path, names, matrix):
    with path.open("w", encoding="utf-8") as f:
        f.write(f"{len(names)} {len(matrix[0])}\n")
        for name, row in zip(names, matrix):
            f.write(f"{name[:10]:<10} {''.join(row)}\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--language-report", required=True)
    ap.add_argument("--matrix-report", required=True)
    args = ap.parse_args()

    d = Path(args.dataset) / "cldf"
    languages = read_csv(d / "languages.csv")
    forms = read_csv(d / "forms.csv")
    cognates = read_csv(d / "cognates.csv")

    wanted = [x for group in LANGUAGES.values() for x in group]
    by_name = {r["Name"]: r for r in languages}

    missing = [x for x in wanted if x not in by_name]
    if missing:
        raise SystemExit("Selected language names not found: " + ", ".join(missing))

    # Keep exactly one variety per selected Name.  The dataset has some
    # varieties sharing Glottocodes; the pilot intentionally uses the named
    # varieties as represented in its own LanguageTable.
    selected = [by_name[x] for x in wanted]
    lang_id = {r["ID"]: r["Name"] for r in selected}
    selected_ids = set(lang_id)

    # Form -> (language, concept).  We need concept presence separately from
    # cognate membership so that absent concepts are '?' rather than 0.
    form_info = {}
    concept_present = defaultdict(set)
    for r in forms:
        if r["Language_ID"] in selected_ids:
            form_info[r["ID"]] = (r["Language_ID"], r["Parameter_ID"])
            concept_present[(r["Language_ID"], r["Parameter_ID"])] = True

    # Cognate set -> selected languages containing a member of that set.
    # We deliberately discard singleton characters for the pilot: a character
    # present in only one taxon contains no internal split information.
    cs_langs = defaultdict(set)
    form_cs = defaultdict(set)
    for r in cognates:
        fid = r.get("Form_ID", "")
        cs = r.get("Cognateset_ID", "")
        if not fid or not cs or fid not in form_info:
            continue
        lid, pid = form_info[fid]
        cs_langs[(pid, cs)].add(lid)
        form_cs[fid].add(cs)

    # Character = a cognate set within a concept.  This mirrors the logic
    # used by comparative-linguistic cognate matrices: cognacy is interpreted
    # within a meaning, not as a global lexical similarity signal.
    chars = []
    for key, lids in cs_langs.items():
        if 2 <= len(lids) < len(selected_ids):
            chars.append(key)
    chars.sort(key=lambda x: (x[0], x[1]))

    # Determine, for each language and concept, whether a form exists.
    lang_concepts = defaultdict(set)
    for lid_pid in concept_present:
        lang_concepts[lid_pid] = True

    # For each selected language/concept/cognate-set:
    #   ? = concept absent from that language
    #   1 = language has a form in that cognate set
    #   0 = concept present, but another cognate set is used
    memberships = defaultdict(set)
    for fid, csets in form_cs.items():
        lid, pid = form_info[fid]
        for cs in csets:
            memberships[(lid, pid, cs)].add(fid)

    matrix = []
    names = []
    for row in selected:
        lid = row["ID"]
        safe = row["Name"].replace(" ", "_").replace("-", "_")
        names.append(safe)
        out = []
        for pid, cs in chars:
            if (lid, pid) not in lang_concepts:
                out.append("?")
            elif (lid, pid, cs) in memberships:
                out.append("1")
            else:
                out.append("0")
        matrix.append(out)

    if not chars:
        raise SystemExit("No variable shared cognate characters survived filtering.")

    # PHYLIP names must be unique; the selected names are checked here.
    if len(names) != len(set(names)):
        raise SystemExit("Duplicate taxon names after sanitization.")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_phylip(out, names, matrix)

    report = Path(args.language_report)
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["division", "name", "ID", "Glottocode", "Latitude", "Longitude"])
        for division, wanted_names in LANGUAGES.items():
            for name in wanted_names:
                r = by_name[name]fMayiKulan
                w.writerow([division, name, r["ID"], r["Glottocode"],
                             r["Latitude"], r["Longitude"]])

    stats = Path(args.matrix_report)
    stats.parent.mkdir(parents=True, exist_ok=True)
    with stats.open("w", encoding="utf-8") as f:
        f.write("Bowern-PNY IQ-TREE pilot\n")
        f.write(f"Selected varieties: {len(selected_ids)}\n")
        f.write(f"Variable shared cognate characters: {len(chars)}\n")
        f.write("Singleton cognate sets excluded: yes\n")
        f.write("Constant characters excluded: yes\n")
        f.write("Missing concepts encoded as ?: yes\n")
        f.write("Present-but-different cognate encoded as 0: yes\n")
        f.write("Shared cognate encoded as 1: yes\n")

if __name__ == "__main__":
    main()
