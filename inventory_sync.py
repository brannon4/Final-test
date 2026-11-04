"""Conservative Row52 inventory reader. Only owner-configured, verified yard URLs.
No automatic fallback to another state's yard or invented vehicles.
"""
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import pandas as pd

COLUMNS=['yard','year','make','model','trim','row','vin','arrival_date','source_url']

def fetch_row52(url, yard, max_pages=5):
    p=urlparse(url)
    if p.scheme!='https' or p.hostname not in ('row52.com','www.row52.com'):
        raise ValueError('Only HTTPS row52.com inventory URLs are supported.')
    if not yard.strip(): raise ValueError('Enter the verified Massachusetts yard name.')
    rows=[]
    session=requests.Session()
    session.headers.update({'User-Agent':'PickProfitMA/1.1 (personal inventory research; contact site for data permissions)'})
    for page in range(1,max_pages+1):
        response=session.get(url,params={'Page':page},timeout=15)
        response.raise_for_status()
        soup=BeautifulSoup(response.text,'html.parser')
        text=soup.get_text(' ',strip=True)
        # Row52 displays a repeating 'Vehicle YEAR MAKE MODEL YARD MMM DD, YYYY VIN' sequence.
        blocks=re.split(r'\bVehicle\b',text)[1:]
        found=0
        for block in blocks:
            block=block[:450]
            m=re.search(r'\b(19\d{2}|20\d{2})\s+(.+?)\s+'+re.escape(yard)+r'\s+([A-Z][a-z]{2}\s+\d{1,2},\s+20\d{2})\s+([A-HJ-NPR-Z0-9]{17})\b',block,re.I)
            if not m: continue
            desc=m.group(2).strip()
            make,_,model=desc.partition(' ')
            rows.append({'yard':yard,'year':int(m.group(1)),'make':make,'model':model,'trim':'','row':'','vin':m.group(4).upper(),'arrival_date':m.group(3),'source_url':url})
            found+=1
        if found==0: break
    if not rows: raise ValueError('No vehicles could be parsed. The site layout, yard name, or access rules may have changed. Use CSV import instead.')
    return pd.DataFrame(rows,columns=COLUMNS).drop_duplicates(subset=['yard','vin'])
