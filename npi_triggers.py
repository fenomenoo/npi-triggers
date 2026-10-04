#!/usr/bin/env python3
"""
npi-triggers: find US healthcare organisations that recently changed.

Pulls the public CMS NPPES registry and classifies organisations by two
computable signals: newly enumerated entities, and established records that
were updated recently.

No API key. No account. No cost. Standard library only.

    python npi_triggers.py IN MI
    python npi_triggers.py FL NC SC --new 90 --changed 60
    python npi_triggers.py CA --taxonomy "Physical Therapist" --cap 2000

Writes npi_triggers.json and tables.md next to this file.

NOTE: a changed record says that something changed, never what. The "changed"
group is a filter, not a verdict. Check a row before acting on it.
"""

import argparse, datetime, io, json, os, sys, time
import urllib.parse, urllib.request

API = "https://npiregistry.cms.hhs.gov/api/"
HERE = os.path.dirname(os.path.abspath(__file__))


def pull(state, taxonomy, cap):
    """Page through the registry for one state. Returns raw records."""
    out, skip = [], 0
    while skip < cap:
        q = urllib.parse.urlencode({
            "version": "2.1", "state": state, "taxonomy_description": taxonomy,
            "enumeration_type": "NPI-2",      # organisations only, never individuals
            "limit": 200, "skip": skip,
        })
        try:
            with urllib.request.urlopen(API + "?" + q, timeout=60) as r:
                data = json.load(r)
        except Exception as e:
            print(f"  ! {state} failed at skip={skip}: {e}", file=sys.stderr)
            break
        results = data.get("results") or []
        if not results:
            break
        out += results
        if len(results) < 200:
            break
        skip += 200
        time.sleep(0.4)                        # be polite to a free public API
    return out


def normalise(record, want_state, today):
    """Keep only records whose PRACTICE address is in the state we asked for.

    The API matches on any address, so a company headquartered elsewhere with a
    mailing address in-state will come back. Those are not local practices.
    """
    basic = record.get("basic", {})
    loc = next((a for a in record.get("addresses", [])
                if a.get("address_purpose") == "LOCATION"), {})
    if (loc.get("state") or "").upper() != want_state:
        return None

    def parse(s):
        try:
            return datetime.date.fromisoformat((s or "")[:10])
        except Exception:
            return None

    enum, upd = parse(basic.get("enumeration_date")), parse(basic.get("last_updated"))
    return {
        "npi": record.get("number"),
        "name": basic.get("organization_name"),
        "city": loc.get("city"),
        "state": loc.get("state"),
        "phone": loc.get("telephone_number"),
        "enum": enum, "upd": upd,
        "enum_age": (today - enum).days if enum else None,
        "upd_age": (today - upd).days if upd else None,
    }


def table(rows, datekey, header):
    rows = sorted(rows, key=lambda r: r[datekey], reverse=True)
    out = [f"| {header} | State | Practice | City | NPI |", "|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r[datekey]} | {r['state']} | {r['name']} | "
                   f"{(r['city'] or '').title()} | {r['npi']} |")
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("states", nargs="+", help="two-letter state codes, e.g. IN MI")
    p.add_argument("--taxonomy", default="Behavior Analyst",
                   help='NPPES taxonomy description (default: "Behavior Analyst")')
    p.add_argument("--new", type=int, default=180,
                   help="days: how recently enumerated counts as a new entity")
    p.add_argument("--changed", type=int, default=120,
                   help="days: how recently an established record changed")
    p.add_argument("--cap", type=int, default=800, help="max records per state")
    args = p.parse_args()

    today = datetime.date.today()
    print(f"Run date {today}. Taxonomy: {args.taxonomy}\n")

    rows = []
    for st in [s.upper() for s in args.states]:
        raw = pull(st, args.taxonomy, args.cap)
        kept = [x for x in (normalise(r, st, today) for r in raw) if x]
        print(f"  {st}: {len(raw)} returned, {len(kept)} actually located in {st}")
        rows += kept

    new = [r for r in rows
           if r["enum_age"] is not None and r["enum_age"] <= args.new]
    changed = [r for r in rows
               if r["enum_age"] and r["enum_age"] > 365
               and r["upd_age"] is not None and r["upd_age"] <= args.changed]

    print(f"\n  {len(rows)} organisations total")
    print(f"  {len(new)} newly enumerated within {args.new} days")
    print(f"  {len(changed)} established but changed within {args.changed} days")

    ser = lambda g: [{**r, "enum": str(r["enum"]), "upd": str(r["upd"])} for r in g]
    with io.open(os.path.join(HERE, "npi_triggers.json"), "w", encoding="utf-8") as f:
        json.dump({"run_date": str(today), "states": args.states,
                   "taxonomy": args.taxonomy,
                   "new": ser(new), "changed": ser(changed)}, f, indent=1)

    with io.open(os.path.join(HERE, "tables.md"), "w", encoding="utf-8") as f:
        f.write(f"_Pulled {today} from the public CMS NPPES registry. "
                f"States: {', '.join(args.states)}. Taxonomy: {args.taxonomy}._\n\n")
        f.write("### A. New entities\n\n" + table(new, "enum", "Enumerated"))
        f.write("\n\n### B. Established, changed recently\n\n"
                + table(changed, "upd", "Record updated") + "\n")

    print("\n  wrote npi_triggers.json and tables.md")
    print("\n  Remember: a changed record says something changed, never what.")
    print("  Section B is a filter, not a verdict. Check each before contact.")


if __name__ == "__main__":
    main()
