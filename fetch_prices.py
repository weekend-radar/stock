"""Fetch SGX prices + 5-year daily history from Yahoo Finance and write data.json.
Run by GitHub Actions (see update-prices.yml). No extra packages needed.
"""
import json, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

# Same codes as the HTML page. SGX stocks use the .SI suffix on Yahoo.
CODES = ["D05","O39","U11","Z74","C38U","A17U","M44U","S63","S58","V03","BN4",
         "BS6","U96","S68","C6L","G13","F34","C09","5E2","U14","ES3"]
EXTRA = {"STI": "^STI"}          # index
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def yahoo_symbol(code):
    return EXTRA.get(code, code + ".SI")


def fetch_json(symbol, tries=3):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol) + "?range=5y&interval=1d")
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:           # network error, 429, etc.
            last = e
            time.sleep(2 * (i + 1))
    raise last


def parse_chart(j):
    res = (j.get("chart") or {}).get("result")
    if not res:
        raise ValueError("no result")
    r = res[0]
    meta = r.get("meta", {})
    ts = r.get("timestamp") or []
    close = (((r.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or []
    off = meta.get("gmtoffset", 28800)
    hist = []
    for t, c in zip(ts, close):
        if c is None:
            continue
        d = (datetime.fromtimestamp(t, tz=timezone.utc) + timedelta(seconds=off)).strftime("%Y-%m-%d")
        hist.append([d, round(c, 3)])
    if len(hist) < 2:
        raise ValueError("too few points")
    price = meta.get("regularMarketPrice", hist[-1][1])
    prev = hist[-2][1]
    return {"p": round(price, 3), "pc": round(prev, 3)}, hist


def main():
    try:
        old = json.load(open("data.json"))
    except Exception:
        old = {"quotes": {}, "history": {}}
    quotes, history, ok = dict(old.get("quotes", {})), dict(old.get("history", {})), 0
    for code in CODES + list(EXTRA):
        try:
            q, h = parse_chart(fetch_json(yahoo_symbol(code)))
            quotes[code], history[code] = q, h
            ok += 1
            print("ok  ", code, q)
        except Exception as e:
            print("FAIL", code, e, file=sys.stderr)
        time.sleep(0.6)               # stay polite, avoid rate limits
    if ok == 0:
        sys.exit("No symbol could be fetched; keeping the old data.json")
    sgt = timezone(timedelta(hours=8))
    out = {"updated": datetime.now(sgt).isoformat(timespec="seconds"),
           "quotes": quotes, "history": history}
    with open("data.json", "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("wrote data.json:", ok, "symbols updated")


if __name__ == "__main__":
    main()
