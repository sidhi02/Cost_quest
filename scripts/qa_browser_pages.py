"""Render every Jinja page and (optionally) test offline browser interactions.

This is an honest offline SCREENING test, not a live Flask-route or retail test.
Preview offers are synthetic and intended for QA ONLY. Run from project root:
    python -m scripts.qa_browser_pages
A compatible installed Chromium may be selected with QA_CHROMIUM_PATH.
"""
import json
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape, StrictUndefined
from core.domain_registry import DOMAIN_INDEX, ALL_CATEGORIES
from services.recommendations import domain_samples, recommend
from services.presentation import prepare_comparison

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts' / 'browser_qa'


def render_pages():
    OUT.mkdir(parents=True,exist_ok=True)
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),
                    autoescape=select_autoescape(['html']),undefined=StrictUndefined)
    endpoints={'index':'index.html','compare':'compare.html','login':'login.html',
               'register':'register.html','account':'account.html','watchlist':'watchlist.html',
               'history':'history.html','admin':'admin.html','logout':'logout.html',
               'account_preferences':'account.html','account_export':'account.html',
               'account_delete':'account.html','account_clear_history':'account.html',
               'watch_add':'compare.html','watch_remove':'watchlist.html'}
    def url_for(endpoint,**kwargs):
        if endpoint=='static':return '../../static/'+kwargs['filename']
        return endpoints.get(endpoint,endpoint+'.html')
    env.globals.update(url_for=url_for,get_flashed_messages=lambda **kw:[])
    user={'id':1,'email':'qa-user@example.invalid','history_enabled':1}
    base={'csrf_token':'offline-qa-fake-token','domains':list(DOMAIN_INDEX.values()),
          'all_categories':ALL_CATEGORIES,'current_user':None,'is_admin':False}
    rows=[]
    for idx,(name,retailer,price,color) in enumerate([
        ('JBL Tune 770NC Bluetooth Headphones Black','Store Alpha',4299,'Black'),
        ('JBL Tune 770NC Bluetooth Headphones Navy','Store Alpha',4299,'Navy'),
        ('JBL Tune 770NC Bluetooth Headphones Black','Store Beta',4799,'Black'),
        ('JBL Tune 770NC Bluetooth Headphones Grey','Store Beta',5199,'Grey'),
    ]):
        rows.append({'name':name,'retailer':retailer,'price':price,'availability':'Available',
                     'match_confidence':'high','product_key':f'{idx:024x}',
                     'comparison_key':'electronics|audio|jbltune770nc|colour='+color,
                     'attributes':{'colour':color},'image':'','source_updated_at':'','url':f'https://example.com/qa/{idx}'})
    verified,_,best=prepare_comparison(rows)
    uncertain=[{'name':'JBL Tune 770NC (colour unspecified)','retailer':'Test Retailer',
                'price':3900,'unverified_attributes':['model colour']}]
    providers=[{'name':'PriceInIndia','role':'Marketplace aggregator','configured':False},
               {'name':'Amazon','role':'Direct retailer','configured':False},
               {'name':'Croma','role':'Direct retailer','configured':False}]
    args={
      'index':('index.html',{'providers':providers,'domain_samples':domain_samples(),'personal_suggestions':[]}),
      'compare':('compare.html',{'query':'JBL Tune 770NC','products':verified,'review_offers':uncertain,
                  'best_price':best,'category_name':'Headphones & Audio','similar_suggestions':recommend('JBL Tune 770NC',limit=4)}),
      'compare_empty':('compare.html',{'query':'Sample unavailable product','products':[], 'review_offers':[],
                  'best_price':None,'category_name':'General','similar_suggestions':[]}),
      'compare_review':('compare.html',{'query':'Samsung Galaxy S25 256GB','products':[],
                  'review_offers':[{'name':'Samsung Galaxy S25','retailer':'Test Retailer','price':54000,'unverified_attributes':['storage']}],
                  'best_price':None,'category_name':'Smartphones','similar_suggestions':recommend('Samsung Galaxy S25 256GB')}),
      'login':('login.html',{'next_url':'index.html'}),
      'register':('register.html',{'next_url':'index.html'}),
      'account':('account.html',{'history':[{'query':'JBL Tune 770NC','searched_at':'2026-11-16 10:00:00'}],
                                'personal_suggestions':recommend('JBL Tune 770NC')}),
      'watchlist':('watchlist.html',{'items':[{'id':1,'retailer':'Demo','product_name':'JBL Tune 770NC',
                    'product_url':'https://example.com/qa'}]}),
      'watchlist_empty':('watchlist.html',{'items':[]}),
      'history':('history.html',{'product_key':'0'*24,'history':[{'retailer':'Demo Store','price':4700,'captured_at':'2026-11-16 10:00:00'}]}),
      'history_empty':('history.html',{'product_key':'0'*24,'history':[]}),
      'error':('error.html',{'message':'This page could not be found.'}),
      'admin':('admin.html',{'provider_status':[{'name':'Demo Provider','role':'Test','configured':False,'message':'Not configured'}],
                 'qa_reports':[{'label':'New matching cases','available':True,'data':{'cases':36,'positive_passes':36,'negative_passes':36}}]})}
    paths={}
    private={'account','watchlist','watchlist_empty','admin'}
    for slug,(template,context) in args.items():
        html=env.get_template(template).render(**{**base, **({'current_user':user} if slug in private else {}),
                                                 **({'is_admin':True} if slug=='admin' else {}),**context})
        path=OUT/(slug+'.html')
        path.write_text(html,encoding='utf8')
        assert '<html' in html and '<main>' in html and '</main>' in html,slug
        paths[slug]=str(path)
    return paths


def screen(paths):
    from playwright.sync_api import sync_playwright
    output={'pages_rendered':len(paths),'browser':'system Chromium','screenshots':[], 'checks':[]}
    chromium_path=os.getenv('QA_CHROMIUM_PATH') or '/usr/bin/chromium'
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=chromium_path,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        for width,height,mode in [(1440,900,'desktop'),(390,844,'mobile')]:
            page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
            errors=[]
            page.on('pageerror',lambda exc:errors.append(str(exc)))
            for slug,path in paths.items():
                # This sandbox blocks local URL navigation. Inject the exact
                # rendered DOM, CSS and JS instead of claiming a Flask E2E test.
                page.set_content(Path(path).read_text(encoding='utf8'),wait_until='load')
                page.add_style_tag(content=(ROOT/'static/css/style.css').read_text(encoding='utf8'))
                page.add_script_tag(content=(ROOT/'static/js/search.js').read_text(encoding='utf8'))
                if slug.startswith('compare'):
                    page.add_script_tag(content=(ROOT/'static/js/comparison.js').read_text(encoding='utf8'))
                page.wait_for_timeout(120)
                assert page.locator('body').is_visible(),slug
                assert page.locator('main').is_visible(),slug
                assert page.locator('h1').count() > 0, f'{mode} {slug}: no h1'
                assert page.evaluate('document.documentElement.scrollWidth')<=width+4, f'Horizontal overflow: {mode} {slug}'
                if slug in {'index','compare','compare_empty','compare_review'}:
                    clear=page.locator('.search-clear')
                    assert clear.is_visible(),f'clear button missing on {slug}'
                    item=page.locator('input[name=q]')
                    item.fill('sample query')
                    clear.click()
                    assert item.input_value()==''
                if slug=='compare':
                    cards=page.locator('#cq-offers .cq-offer')
                    assert cards.count()==3,'Expected same-price colours grouped'
                    assert cards.first.get_attribute('data-price')=='4299', 'Cheapest not first'
                    page.select_option('#cq-sort','high')
                    assert cards.first.get_attribute('data-price')=='5199','Sort descending broken'
                    page.select_option('#cq-store-filter','store alpha')
                    assert page.locator('#cq-offers .cq-offer:visible').count()==1,'Retailer filter broken'
                    page.select_option('#cq-store-filter','all')
                    page.select_option('#cq-sort','low')
                if slug=='compare_review':
                    assert page.locator('.cq-empty').is_visible()
                    assert page.locator('.cq-review').count()==1
                if slug in {'index','compare','compare_review','login','register','account','watchlist','history','admin'}:
                    name=f'{slug}_{mode}.png'
                    page.screenshot(path=str(OUT/name),full_page=True)
                    output['screenshots'].append(name)
                output['checks'].append(f'{mode}: {slug} renders, h1 and no horizontal overflow')
            assert not errors,errors
            page.close()
        browser.close()
    return output


def main():
    paths=render_pages()
    result={'mode':'offline Jinja rendering and browser UI, NO Flask or retailer network','pages_rendered':len(paths)}
    try:
        result.update(screen(paths))
        result['browser_passed']=True
    except (ImportError,Exception) as exc:
        result['browser_passed']=False
        result['browser_error']=str(exc)
    (OUT/'report.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
    if not result.get('browser_passed'):
        raise SystemExit(1)


if __name__=='__main__':
    main()
