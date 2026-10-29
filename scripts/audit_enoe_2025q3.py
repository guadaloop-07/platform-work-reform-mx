"""Audit the reviewed official ENOE archive, producing aggregate counts only."""

import collections
import csv
import hashlib
import io
import json
import zipfile

path = "data/enoe/official/2025q3/enoe-2025q3-official.zip"
expected_sha256 = "7138b2bfabc740a9805b83b3fd0dae28287fc2aab3781a596a741b8fc7861566"
with open(path, "rb") as archive:
    if hashlib.file_digest(archive, "sha256").hexdigest() != expected_sha256:
        raise ValueError("Archive differs from the audited 2025 Q3 release")
dwelling = ("tipo", "mes_cal", "cd_a", "cve_ent", "con", "v_sel")
household = (*dwelling, "n_hog", "h_mud")
person = (*household, "n_ren")
fields = {"viv": dwelling, "hog": household, "sdem": person, "coe1": person, "coe2": person}
report = {}
keys = {}
with zipfile.ZipFile(path) as z:
    for table, key in fields.items():
        base = f"conjunto_de_datos_{table}_enoe_2025_3t"
        data = f"{base}/conjunto_de_datos/{base}.csv"
        dictionary = f"{base}/diccionario_de_datos/diccionario_datos_{table}_enoe_2025_3t.csv"
        sha = hashlib.sha256()
        with z.open(data) as raw:
            while chunk := raw.read(1024 * 1024):
                sha.update(chunk)
        with z.open(dictionary) as raw:
            dictionary_bytes = raw.read()
        definitions = list(
            csv.DictReader(io.StringIO(dictionary_bytes.decode("utf-8"), newline=""))
        )
        dictionary_columns = [item["NEMÓNICO"] for item in definitions]
        observed = set()
        duplicates = blanks = count = 0
        diagnostics = collections.Counter()
        with (
            z.open(data) as raw,
            io.TextIOWrapper(raw, encoding="cp1252", errors="strict", newline="") as text,
        ):
            reader = csv.DictReader(text, strict=True)
            header = reader.fieldnames
            for row in reader:
                count += 1
                if None in row or any(v is None for v in row.values()):
                    raise ValueError(f"{table}: malformed row {count}")
                k = tuple(row[col] for col in key)
                blanks += any(not value.strip() for value in k)
                duplicates += k in observed
                observed.add(k)
                if table == "sdem":
                    diagnostics[(row["eda"], row["c_res"])] += 1
        keys[table] = observed
        report[table] = {
            "rows": count,
            "columns": len(header),
            "header_matches_dictionary": header == dictionary_columns,
            "missing_key_columns": sorted(set(key) - set(header)),
            "duplicates": duplicates,
            "blank_keys": blanks,
            "sha256": sha.hexdigest(),
            "dictionary_sha256": hashlib.sha256(dictionary_bytes).hexdigest(),
        }
        if table == "sdem":
            report[table]["age_under_12"] = sum(
                n
                for (age, _), n in diagnostics.items()
                if age == "99" or (age.isdigit() and int(age) < 12)
            )
    for parent, child in [
        ("viv", "hog"),
        ("hog", "sdem"),
        ("sdem", "coe1"),
        ("sdem", "coe2"),
        ("coe1", "coe2"),
    ]:
        pk, ck = keys[parent], keys[child]
        width = len(fields[parent])
        matched = [key for key in ck if key[:width] in pk]
        covered = {key[:width] for key in matched}
        report[f"{parent}_{child}"] = {
            "parent": len(pk),
            "child": len(ck),
            "matched_child": len(matched),
            "orphan_child": len(ck) - len(matched),
            "parent_without_child": len(pk - covered),
        }
    household_covered = {key[: len(household)] for key in keys["sdem"]}
    for table in ("hog", "sdem"):
        base = f"conjunto_de_datos_{table}_enoe_2025_3t"
        data = f"{base}/conjunto_de_datos/{base}.csv"
        categories = collections.Counter()
        unexplained_ages = collections.Counter()
        with (
            z.open(data) as raw,
            io.TextIOWrapper(raw, encoding="cp1252", errors="strict", newline="") as text,
        ):
            for row in csv.DictReader(text, strict=True):
                key = tuple(row[col] for col in fields[table])
                if table == "hog" and key not in household_covered:
                    categories[row["r_def"]] += 1
                if table == "sdem" and key not in keys["coe1"]:
                    age = row["eda"]
                    age_group = (
                        "under12"
                        if age == "99" or (age.isdigit() and int(age) < 12)
                        else "12_or_more_or_missing"
                    )
                    categories[(age_group, row["r_def"], row["c_res"])] += 1
                    if (
                        age_group != "under12"
                        and row["r_def"] == "0"
                        and row["c_res"] in ("1", "3")
                    ):
                        age_label = "99" if age == "99" else "other"
                        unexplained_ages[age_label] += 1
        report[f"{table}_without_child_categories"] = {str(k): v for k, v in categories.items()}
        if table == "sdem":
            report["unmatched_complete_interview_resident_ages"] = dict(unexplained_ages)
print(json.dumps(report, indent=2, ensure_ascii=False))
