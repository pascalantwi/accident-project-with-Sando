"""Plain-language names for road cells, for tables and maps aimed at decision makers.

A cell's name combines its route, the most frequent landmark in its incident descriptions
(interchange, bridge, ramp), its county and its median mile marker, for example
"I-295 W at Buckman Bridge (Duval County, MM 12)".
"""
import re

import numpy as np
import pandas as pd

from common import WORK



def clean_descriptor(text):
    """'At Buckman Bridge' -> 'at Buckman Bridge'; 'Before between A/B' -> 'between A and B'."""
    t = text.strip()
    rules = [(r"^(?:Before|Beyond) between (.+)/(.+)$", r"between \1 and \2"),
             (r"^Ramp (To|From) (.+)$", lambda m: f"at ramp {m.group(1).lower()} {m.group(2)}"),
             (r"^At MM (\S+)$", r"near MM \1"), (r"^Beyond MM (\S+)$", r"past MM \1"),
             (r"^Before MM (\S+)$", r"before MM \1"), (r"^At (.+)$", r"at \1"),
             (r"^Beyond (.+)$", r"past \1"), (r"^Before (.+)$", r"before \1")]
    for pat, rep in rules:
        if re.match(pat, t):
            return re.sub(pat, rep, t)
    return t


def cell_names():
    inc = pd.read_parquet(WORK / "incidents.parquet")
    desc = inc["roadway"].str.split(",", n=1).str[1].fillna("").str.strip()
    inc = inc.assign(desc=desc, landmark=~desc.str.contains(r"\bMM\b"))

    def name(g):
        route = g["route"].mode().iat[0]
        county = g["county"].mode().iat[0] if g["county"].notna().any() else None
        lm = g.loc[g["landmark"], "desc"]
        lm = lm[~lm.str.contains(re.escape(route))]           # "At I-295 E" on I-295 E is not a landmark
        mm = g["mile_marker"].median()
        if len(lm):
            d = clean_descriptor(lm.mode().iat[0])
        elif pd.notna(mm):
            d = f"near MM {mm:.0f}"
        else:
            d = clean_descriptor(g["desc"].mode().iat[0])
        extra = ", ".join(x for x in [f"{county} County" if county else None,
                                      f"MM {mm:.0f}" if pd.notna(mm) and "MM" not in d else None] if x)
        return pd.Series({"route": route, "county": county, "mile_marker": None if pd.isna(mm) else round(mm),
                          "name": " ".join(x for x in [route, d] if x) + (f" ({extra})" if extra else "")})

    return inc.groupby("cell").apply(name, include_groups=False)


if __name__ == "__main__":
    n = cell_names()
    n.to_csv(WORK / "cell_names.csv")
    print(n.sample(12, random_state=3)["name"].to_string())
