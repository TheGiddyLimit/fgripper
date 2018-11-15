import bs4
import re

orig_prettify = bs4.BeautifulSoup.prettify
r = re.compile(r'^(\s*)', re.MULTILINE)
def prettify(self, encoding=None, formatter="minimal", indent_width=4):
    return r.sub(r'\1' * indent_width, orig_prettify(self, encoding, formatter))
bs4.BeautifulSoup.prettify = prettify

with open("C://repos/fgripper/adventures/DD Storm King's Thunder/db-cleaned.xml", encoding='cp1252') as html:
    soup = bs4.BeautifulSoup(html, 'html.parser')

    # for elem in soup.find_all('category', {"name": "The Tome of Beasts"}):
    #     if elem is not None:
    #         elem.unwrap()

    with open("trash/db-cleaned.xml", "wb") as file:
        file.write(soup.prettify(encoding="cp1252"))
