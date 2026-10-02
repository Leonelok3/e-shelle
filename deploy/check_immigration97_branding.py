"""Read-only checks of public pages; never logs in or sends payment requests."""
import re
from html.parser import HTMLParser
from urllib.parse import urlparse
import requests

class VisibleContent(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.text = []
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag == "a":
            self.links.extend(value for key, value in attrs if key == "href" and value)
    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)

paths = ["/canada/", "/prep/", "/prep/fr/tcf/", "/prep/fr/tcf/du-jour/",
         "/accounts/login/", "/accounts/register/", "/accounts/upgrade/?app=prep",
         "/billing/access/", "/cgu/", "/terms/", "/jobs/canada/",
         "/jobs/canada/bourses/", "/canada/programmes/"]
for path in paths:
    response = requests.get("https://immigration97.com" + path, timeout=30)
    response.raise_for_status()
    assert urlparse(response.url).hostname in ("immigration97.com", "www.immigration97.com"), path
    parser = VisibleContent()
    parser.feed(response.text)
    assert not re.search(r"e[- ]shelle|237680625082|680\s*625\s*082", " ".join(parser.text), re.I), path
    assert not any("e-shelle.com" in link or "237680625082" in link for link in parser.links), path
    print("OK", path)
for asset in ("css/tcf-daily.css", "js/tcf-daily.js", "img/immigration97-logo.png"):
    response = requests.get("https://immigration97.com/static/" + asset, timeout=30)
    response.raise_for_status()
    assert response.content, asset
    print("OK static", asset)
