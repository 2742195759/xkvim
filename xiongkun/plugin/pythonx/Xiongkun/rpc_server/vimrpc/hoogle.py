import os
import sys
import json
import time
from .decorator import *
import requests  
import json
from bs4 import BeautifulSoup as Soup
from dataclasses import dataclass

@dataclass
class HoogleResult: 
    signature: str
    package: str
    document: str
    example: str

    def to_markdown(self):
        output = []
        output.append(f'**{self.signature}**')
        output.append(f"**Package:** {self.package}")
        output.append(f"==========================\n")
        output.append(f"**Document:** \n{self.document}\n")
        if self.example:
            output.append(f"**Example:** \n{self.example}\n")
        return "\n".join(output)
  
def hoogle_search(keyword): 
    url = f'https://hoogle.haskell.org/?hoogle={keyword}&scope=set%3Astackage'  
    response = requests.get(url, timeout=5)  
    soup = Soup(response.text, 'html.parser')
    items = soup.css.select('div.result')
    results = []
    for item in items: 
        sig = item.css.select("div.ans")[0].get_text()
        pac = item.css.select("div.from")[0].get_text()
        doc = item.css.select("div.doc")[0].get_text()
        try: 
            exp = item.css.select("pre")[0].get_text()
        except:
            exp = ""
        results.append(HoogleResult(sig, pac, doc, exp))
    return results

class HoogleSearcher(Service):
    def __init__(self, queue):
        self.last = []

    @server_function
    def search(self, keyword):
        results = hoogle_search(keyword)
        self.last = results
        return [item.to_markdown() for item in self.last]

if __name__ == "__main__":
    from server_cluster import ServerCluster, printer_process_fn
    servers = ServerCluster()
    servers.start_queue(printer_process_fn)
    fn = servers.get_server_fn("hoogle.search")
    print (fn (1, "insert")[2])
    time.sleep(3)
    servers.stop()
