"""Keep the manuscript's numbered references (IEEE style) in order of first citation, with in-text
citations that link to the cited work on the internet.

References are written as  <a id="ref-KEY"></a>[n] Author, "Title," ..., doi: 10.xxxx/yyyy.
                      or   <a id="ref-KEY"></a>[n] Author, "Title," ... [Online]. Available: URL
In the text a citation is  [[n]](https://doi.org/10.xxxx/yyyy "ref-KEY")
(a new citation may be typed as [[0]](#ref-KEY); this script fills in its link and number).

The link is the DOI resolver when the reference has a DOI, otherwise its official URL, otherwise a
Google Scholar search for its exact title. Running the script renumbers the reference list by first
citation (references not yet cited keep their relative order after the cited ones), rewrites every
in-text number and link, and makes DOIs and URLs in the reference list clickable.

Usage: python src/manuscript/references.py [manuscript/manuscript_draft.md]
"""
import pathlib
import re
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[2]
REF_LINE = re.compile(r'^<a id="ref-([\w-]+)"></a>\[\d+\] (.*)$', re.M)
CITE = re.compile(r'\[\[\d+\]\]\((?:#ref-([\w-]+)|[^"\s]+ "ref-([\w-]+)")\)')
LINK = re.compile(r"\[([^\]]+)\]\((https?://(?:[^()\s]|%2[89])+)\)")


def safe(url):
    """Percent-encode parentheses so URLs (e.g. DOIs such as 10.1061/(ASCE)...) work in markdown links."""
    return url.replace("(", "%28").replace(")", "%29")


def plain(text):
    """Reference text with any markdown links reduced to their label."""
    return LINK.sub(r"\1", text)


def target(text):
    t = plain(text)
    doi = re.search(r"doi:\s*(10\.\S+?)\.?$", t)
    if doi:
        return safe("https://doi.org/" + doi.group(1))
    url = re.search(r"Available:\s*(https?://\S+?)\.?$", t)
    if url:
        return safe(url.group(1))
    title = re.search(r'"([^"]+?),?"', t)
    query = f'"{title.group(1)}"' if title else t[:120]
    return "https://scholar.google.com/scholar?q=" + urllib.parse.quote(query)


def linkify(text):
    """Make the DOI and URL in a reference clickable."""
    t = plain(text)
    t = re.sub(r"doi:\s*(10\.\S+?)(\.?)$", lambda m: f"doi: [{m.group(1)}]({safe('https://doi.org/' + m.group(1))}){m.group(2)}", t)
    t = re.sub(r"Available:\s*(https?://\S+?)(\.?)$", lambda m: f"Available: [{m.group(1)}]({safe(m.group(1))}){m.group(2)}", t)
    return t


def renumber(path):
    s = path.read_text()
    head, sep, rest = s.partition("## References\n")
    end = rest.find("\n---\n")
    block, tail = rest[:end], rest[end:]
    refs = REF_LINE.findall(block)
    keys = [k for k, _ in refs]
    if len(set(keys)) != len(keys):
        raise SystemExit(f"duplicate reference keys: {sorted(k for k in keys if keys.count(k) > 1)}")
    body = head + tail
    cited = list(dict.fromkeys(a or b for a, b in CITE.findall(body)))
    missing = [k for k in cited if k not in keys]
    if missing:
        raise SystemExit(f"cited but not in the reference list: {missing}")
    order = cited + [k for k in keys if k not in cited]
    number = {k: i + 1 for i, k in enumerate(order)}
    text_of = dict(refs)
    url = {k: target(t) for k, t in refs}

    def fix(t):
        return CITE.sub(lambda m: (lambda k: f'[[{number[k]}]]({url[k]} "ref-{k}")')(m.group(1) or m.group(2)), t)

    block = "\n" + "\n\n".join(f'<a id="ref-{k}"></a>[{number[k]}] {linkify(text_of[k])}' for k in order) + "\n"
    path.write_text(fix(head) + sep + block + fix(tail))
    scholar = [k for k in cited if "scholar.google" in url[k]]
    print(f"{len(cited)} cited, {len(order) - len(cited)} not yet cited; "
          f"{sum('doi.org' in url[k] for k in cited)} link to DOIs, {len(scholar)} to Google Scholar {scholar}")


if __name__ == "__main__":
    renumber(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "manuscript" / "manuscript_draft.md")
