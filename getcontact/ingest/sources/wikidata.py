"""Wikidata: companies that have an official website, plus their CEOs, founders, chairs, directors and board members.

Free SPARQL endpoint, CC0 data. Be polite: 1 request/sec, descriptive User-Agent. Queries are kept lean
(no label service, few OPTIONALs) to stay under Wikidata's 60 s limit at deep offsets.
    python -m ingest.run wikidata --limit 20000
    python -m ingest.run wikidata --country IN
"""
import time

SPARQL = "https://query.wikidata.org/sparql"
TYPES = "wd:Q4830453 wd:Q891723 wd:Q6881511 wd:Q783794 wd:Q1589009 wd:Q2995256 wd:Q18388277 wd:Q1058914"
ROLES = {"P169": "Chief Executive Officer", "P112": "Founder", "P488": "Chairperson", "P1037": "Director / Manager", "P3320": "Board Member", "P1789": "Chief Operating Officer"}

Q_COMPANIES = """
SELECT ?company ?label ?website ?cc ?employees ?li WHERE {
  VALUES ?type { %s }
  ?company wdt:P31 ?type ; wdt:P856 ?website ; rdfs:label ?label .
  FILTER(LANG(?label) = "en")
  %s
  OPTIONAL { ?company wdt:P17 ?c . ?c wdt:P297 ?cc . }
  OPTIONAL { ?company wdt:P1128 ?employees . }
  OPTIONAL { ?company wdt:P4264 ?li . }
} LIMIT %d OFFSET %d
"""
Q_INDUSTRY = """
SELECT ?company ?ilabel ?inception WHERE {
  VALUES ?company { %s }
  OPTIONAL { ?company wdt:P452 ?industry . ?industry rdfs:label ?ilabel . FILTER(LANG(?ilabel) = "en") }
  OPTIONAL { ?company wdt:P571 ?inception . }
}
"""
Q_PEOPLE = """
SELECT ?company ?p ?person ?label ?li WHERE {
  VALUES ?company { %s }
  VALUES ?p { %s }
  ?company ?p ?person .
  ?person wdt:P31 wd:Q5 ; rdfs:label ?label .
  FILTER(LANG(?label) = "en")
  OPTIONAL { ?person wdt:P6634 ?li . }
}
"""


def add_args(p):
    p.add_argument("--country", help="ISO-2 code filter")
    p.add_argument("--page", type=int, default=200)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--no-people", action="store_true")


def _q(ing, query):
    r = ing.get(SPARQL, params={"query": query, "format": "json"}, headers={"Accept": "application/sparql-results+json"}, timeout=90)
    if r.status_code != 200:
        ing.log(f"SPARQL {r.status_code}: {r.text[:200]}")
        return []
    return r.json()["results"]["bindings"]


def _v(b, k):
    return b[k]["value"] if k in b else None


def _qid(b, k):
    return _v(b, k).rsplit("/", 1)[-1]


def run(ing, args):
    offset, total = args.offset, 0
    cfilter = f'?company wdt:P17 ?cnode . ?cnode wdt:P297 "{args.country}" .' if args.country else ""
    props = " ".join(f"wdt:{p}" for p in ROLES)
    while True:
        rows = _q(ing, Q_COMPANIES % (TYPES, cfilter, args.page, offset))
        if not rows:
            break
        batch = {}
        for b in rows:
            qid = _qid(b, "company")
            emp = _v(b, "employees")
            li = _v(b, "li")
            o = ing.upsert_org(_v(b, "label"), qid, website=_v(b, "website"), country=_v(b, "cc"),
                               employee_count=int(float(emp)) if emp else None,
                               linkedin_url=f"https://www.linkedin.com/company/{li}" if li else None,
                               source_url=f"https://www.wikidata.org/wiki/{qid}")
            if o:
                batch[qid] = o
            total += 1
        ing.commit()
        if batch:
            qids = " ".join(f"wd:{q}" for q in batch)
            time.sleep(1)
            for b in _q(ing, Q_INDUSTRY % qids):
                o = batch.get(_qid(b, "company"))
                inc = _v(b, "inception")
                if o:
                    if _v(b, "ilabel") and not o.industry:
                        o.industry = _v(b, "ilabel")
                    if inc and inc[:4].isdigit() and not o.founded_year:
                        o.founded_year = int(inc[:4])
            if not args.no_people:
                time.sleep(1)
                for b in _q(ing, Q_PEOPLE % (qids, props)):
                    o = batch.get(_qid(b, "company"))
                    pid, prop, li = _qid(b, "person"), _qid(b, "p"), _v(b, "li")
                    ing.upsert_person(_v(b, "label"), f"{pid}:{_qid(b, 'company')}", o, title=ROLES.get(prop, "Executive"),
                                      country=o.country if o else None, linkedin_url=f"https://www.linkedin.com/in/{li}" if li else None,
                                      source_url=f"https://www.wikidata.org/wiki/{pid}")
            ing.commit()
        ing.progress()
        offset += args.page
        if args.limit and total >= args.limit:
            break
        if len(rows) < args.page:
            break
        time.sleep(1)
