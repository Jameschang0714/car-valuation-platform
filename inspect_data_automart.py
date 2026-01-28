from bs4 import BeautifulSoup
import json

def inspect():
    with open("automart_bypass_toyota-vios.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    data_tag = soup.find('script', id='__NEXT_DATA__')
    
    if data_tag:
        data = json.loads(data_tag.string)
        with open("automart_dump.json", "w", encoding="utf-8") as out:
            json.dump(data, out, indent=2)
        print("Dumped JSON to automart_dump.json")
        try:
            inner = data['props']['pageProps']['data']
            print("Checking 'article'...")
            article = inner.get('article', {})
            print("Article keys:", article.keys())
            
            print("Checking 'landingPage'...")
            lp = inner.get('landingPage', {})
            print("LandingPage keys:", lp.keys())
            
            # Use recursive search for "price" key again but limited to these objects if I can
            # But let's just dump their content to see structure
            # print("LandingPage content snippet:", json.dumps(lp, indent=2)[:500])
        except KeyError as e:
            print(f"KeyError: {e}")

if __name__ == "__main__":
    inspect()
