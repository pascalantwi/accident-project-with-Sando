"""Keep the manuscript's numbered references (IEEE style) in order of first citation.

References are written as  <a id="ref-KEY"></a>[n] Author, "Title," ...
and cited in the text as   [[n]](#ref-KEY)   (several: [[1]](#ref-a), [[2]](#ref-b)).
Running this script renumbers the reference list by first citation in the text (references not yet
cited keep their relative order after the cited ones) and rewrites every in-text number.

Usage: python src/manuscript/references.py [manuscript/manuscript_draft.md]
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REF_LINE = re.compile(r'^(?:<a id="ref-([\w-]+)"></a>)?\[\d+\] (.*)$', re.M)
CITE = re.compile(r"\[\[\d+\]\]\(#ref-([\w-]+)\)")


def default_key(text):
    """'Y. Benjamini and Y. Hochberg, "...", 1995.' -> 'benjamini1995'."""
    first = text.split('"')[0].split(",")[0].split(" and ")[0].strip()
    m = re.match(r"^(?:[A-Z][a-z]?\.[\s-]*)+(.+)$", first)
    name = m.group(1) if m and not first.startswith("U.S.") else first
    year = re.findall(r"\b(19\d\d|20\d\d)\b", text)
    return re.sub(r"[^a-z]", "", name.lower())[:20] + (year[-1] if year else "")


def renumber(path):
    s = path.read_text()
    head, sep, rest = s.partition("## References\n")
    end = rest.find("\n---\n")
    block, tail = rest[:end], rest[end:]
    refs = [(key or default_key(text), text) for key, text in REF_LINE.findall(block)]
    keys = [k for k, _ in refs]
    if len(set(keys)) != len(keys):
        raise SystemExit(f"duplicate reference keys: {sorted(k for k in keys if keys.count(k) > 1)}")
    body = head + tail                                   # citations may appear in appendix captions too
    cited = list(dict.fromkeys(CITE.findall(body)))
    missing = [k for k in cited if k not in keys]
    if missing:
        raise SystemExit(f"cited but not in the reference list: {missing}")
    order = cited + [k for k in keys if k not in cited]
    number = {k: i + 1 for i, k in enumerate(order)}
    text_of = dict(refs)
    fix = lambda t: CITE.sub(lambda m: f"[[{number[m.group(1)]}]](#ref-{m.group(1)})", t)  # noqa: E731
    block = "\n" + "\n\n".join(f'<a id="ref-{k}"></a>[{number[k]}] {text_of[k]}' for k in order) + "\n"
    path.write_text(fix(head) + sep + block + fix(tail))
    print(f"{len(cited)} cited, {len(order) - len(cited)} not yet cited")


if __name__ == "__main__":
    renumber(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "manuscript" / "manuscript_draft.md")
