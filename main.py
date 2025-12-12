import pandas as pd 
import requests 
from bs4 import BeautifulSoup 
from urllib .parse import urljoin 

def extract_logo (domain ):
    url =f"https://{domain }"
    try :
        response =requests .get (url ,timeout =10 ,allow_redirects =True )
        soup =BeautifulSoup (response .content ,'html.parser')
        base =response .url 
        for img in soup .find_all ('img'):
            classes =' '.join (img .get ('class',[])).lower ()
            if 'logo'in classes :
                src =img .get ('src')
                if src :
                    return urljoin (base ,src )
        return None 
    except :
        return None 
df =pd .read_parquet ('logos.snappy.parquet')
domains =df ['domain'].tolist ()
logos ={}
for i ,domain in enumerate (domains ,1 ):
    print (f"[{i }/{len (domains )}] {domain }",end ='\r')
    logo_url =extract_logo (domain )
    if logo_url :
        logos [domain ]=logo_url 

print (f"\nExtracted: {len (logos )}/{len (domains )} = {len (logos )/len (domains )*100 :.1f}%")