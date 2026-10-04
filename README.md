# npi-triggers

Finds US healthcare organisations that **recently changed**, using the public
CMS provider registry. No API key, no account, no cost.

Most prospecting tools answer "who exists". This answers "who changed, and
when" — which is the only part that tells you whether a conversation is worth
having this month.

---

## What it does

The CMS NPPES registry is a federal public record of every provider and
provider organisation in the United States. Every record carries two dates:

- **`enumeration_date`** — when the organisation was created
- **`last_updated`** — when its record last changed

Those two fields make two things computable that you otherwise have to guess at.

**New entities.** A Type 2 NPI created inside your window is an organisation
that did not exist before: a new practice, or an existing owner standing up a
second entity. This signal is firm. An enumeration date cannot mean anything
else.

**Established organisations that just changed.** Enumerated over a year ago,
record updated inside your window. Address changes, new locations and ownership
changes all surface here.

The script pulls a state, filters to organisations whose **practice** address is
actually in that state, classifies them, and writes a markdown table and a JSON
file.

## The limit, stated up front

**A changed record tells you something changed. It never tells you what.**

The registry publishes the date of the last update and does not expose a diff.
That date moves for a new address, a second location or an ownership change. It
also moves for a corrected fax number.

So the "changed" group is **a filter, not a verdict.** Every row needs a human
check before anyone acts on it, and some will turn out to be nothing.

It is still far cheaper than working an entire state in alphabetical order, and
a tool that is honest about what it cannot see is more useful than one that
isn't. The "new entities" group does not have this problem.

---

## Why it exists, and what it returned

Two companies selling automation into US therapy and medical practices describe
the same problem in their own job listings: the practices worth contacting are
not the ones a database will hand you, and finding them is a reading job rather
than a filtering one. **Solum Health** (YC S22) builds revenue-cycle automation
for ABA and outpatient therapy. **Eurovensys** builds and sells software into US
clinics.

Neither of them commissioned this. I wrote it to answer the problem they both
described, because an argument about targeting is worth less than the list.

**First run, 4 October 2026, Indiana and Michigan, taxonomy `Behavior Analyst`:**

| | |
|---|---|
| Organisations with a practice address in those states | **789** |
| Newly enumerated within 180 days | **38** |
| Established but record-updated within 120 days | **41** |
| Out-of-state records correctly discarded in Indiana alone | **175 of 464** |

Every row is a real organisation with a real NPI and a real date. Runs in about
thirty seconds.

The out-of-state number is the part that surprised me: **38% of what the API
returns for a state is not located in that state.** See below for why.

## Install

Python 3.8 or newer. Nothing else — it uses only the standard library.

```bash
git clone https://github.com/fenomenoo/npi-triggers.git
cd npi-triggers
```

## Use

```bash
python npi_triggers.py IN MI
```

```
Run date 2026-10-04. Taxonomy: Behavior Analyst

  IN: 464 returned, 339 actually located in IN
  MI: 482 returned, 450 actually located in MI

  789 organisations total
  38 newly enumerated within 180 days
  41 established but changed within 120 days

  wrote npi_triggers.json and tables.md
```

Writes `tables.md` (paste-ready) and `npi_triggers.json` (for a CRM or a sheet).
Both are gitignored, because they are lists of real businesses.

### Options

```bash
# any states
python npi_triggers.py FL NC SC TX

# any specialty — the string must match the registry's own wording
python npi_triggers.py CA --taxonomy "Physical Therapist"
python npi_triggers.py NY --taxonomy "Occupational Therapist"
python npi_triggers.py IL --taxonomy "Speech-Language Pathologist"

# tighter windows give fewer, hotter rows
python npi_triggers.py IN --new 90 --changed 60

# raise the cap for large states
python npi_triggers.py CA TX --cap 2000
```

| Flag | Default | What it does |
|---|---|---|
| `--taxonomy` | `Behavior Analyst` | NPPES taxonomy description |
| `--new` | `180` | days: how recent counts as a new entity |
| `--changed` | `120` | days: how recent counts as a changed record |
| `--cap` | `800` | max records pulled per state |

---

## Why the state filter is not redundant

The NPPES API matches on **any** address attached to a record, including
mailing addresses. Asking for `state=IN` returns organisations headquartered in
New Jersey, Georgia and Texas that happen to have an Indiana mailing address.

In the run above that was **175 of 464 records in Indiana — 38% noise.** The
script keeps only records whose `LOCATION` address is in the state you asked
for, because a company with a PO box in a state is not a practice in it.

## Pair it with something dated

A registry change tells you one organisation moved. It is much stronger
alongside an event that moved a whole market on a known date — a state Medicaid
policy change, a reimbursement rule, a licensure requirement. Those are
published with effective dates.

One organisation that changed, inside a state that changed, in the same month,
is a far better reason to make contact than either on its own.

## Being decent about it

These are real small businesses in a public record. The registry exists so
patients and payers can verify providers.

Don't publish lists generated by this. Don't contact anyone with under 30 days
of history — a brand new practice has no claims yet, so there is usually
nothing to talk about. And check a row before you act on it, because the limit
above is real.

## Licence

MIT.
