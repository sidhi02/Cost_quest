"""New hand-labelled offline offer-pair checks, independent of legacy 61 fixtures.

These cases measure matching logic only. They do not fetch retailer prices and
must never be reported as a live shopping availability test.
"""
import json
from pathlib import Path
from collections import Counter
from services.product_intelligence import process_offers

CASES = [
 ('electronics','Logitech MX Master 3S Wireless Mouse','Logitech MX Master 3S Bluetooth Wireless Mouse','Logitech MX Master 2S Wireless Mouse'),
 ('electronics','Canon EOS R50 Camera','Canon EOS R50 Mirrorless Camera','Canon EOS R10 Camera'),
 ('electronics','JBL Tune 770NC Headphones','JBL Tune 770NC Bluetooth Headphones','JBL Tune 760NC Bluetooth Headphones'),
 ('electronics','Acer Nitro V 15 RTX 4050','Acer Nitro V 15 laptop RTX 4050','Acer Nitro V 15 laptop RTX 3050'),
 ('electronics','Samsung Galaxy Tab S9 FE 128GB','Samsung Galaxy Tab S9 FE Tablet 128GB','Samsung Galaxy Tab S9 FE Tablet 256GB'),
 ('electronics','Apple Watch Series 9 45mm','Apple Watch Series 9 45mm GPS','Apple Watch Series 9 41mm GPS'),
 ('fashion','Adidas Ultraboost 5 UK 9','Adidas Ultraboost 5 Running Shoes UK 9','Adidas Ultraboost 5 Running Shoes UK 8'),
 ('fashion','Puma Smash V2 Sneakers UK 8','Puma Smash V2 Sneakers UK 8','Puma Smash V2 Sneakers UK 9'),
 ('fashion',"Levis 511 Slim Fit Jeans Size 32",'Levis 511 Slim Fit Denim Jeans Size 32','Levis 511 Slim Fit Denim Jeans Size 34'),
 ('fashion','Fastrack Analog Wrist Watch','Fastrack Analog Wrist Watch','Fastrack Digital Wrist Watch'),
 ('fashion','Ray Ban Polarized Sunglasses','Ray Ban Polarized Sunglasses','Ray Ban Optical Frame Eyeglasses'),
 ('fashion','Allen Solly Cotton Shirt Size L','Allen Solly Cotton Shirt Size L','Allen Solly Cotton Shirt Size M'),
 ('home_appliances','Voltas 1.5 Ton Inverter AC','Voltas 1.5 Ton Inverter Air Conditioner','Voltas 2 Ton Inverter Air Conditioner'),
 ('home_appliances','Bosch 8kg Front Load Washing Machine','Bosch 8kg Front Load Washing Machine','Bosch 9kg Front Load Washing Machine'),
 ('home_appliances','Whirlpool 265L Double Door Refrigerator','Whirlpool 265L Double Door Refrigerator','Whirlpool 300L Double Door Refrigerator'),
 ('home_appliances','Philips 4L Air Fryer','Philips 4L Air Fryer','Philips 6L Air Fryer'),
 ('home_appliances','IFB 30L Convection Microwave','IFB 30L Convection Microwave','IFB 23L Convection Microwave'),
 ('home_appliances','LG 5 Star 1.5 Ton Inverter AC','LG 5 Star 1.5 Ton Inverter AC','LG 3 Star 1.5 Ton Inverter AC'),
 ('books_stationery','Deep Work Paperback English','Deep Work English Paperback Book','Deep Work English Hardcover Book'),
 ('books_stationery','Ikigai Hindi Paperback','Ikigai Hindi Paperback Book','Ikigai English Paperback Book'),
 ('books_stationery','Classmate 200 Pages Notebook Pack of 6','Classmate 200 Pages Notebook Pack of 6','Classmate 200 Pages Notebook Pack of 4'),
 ('books_stationery','Oxford English Dictionary 3rd Edition','Oxford English Dictionary 3rd Edition','Oxford English Dictionary 2nd Edition'),
 ('books_stationery','Cello Gel Pen Pack of 10','Cello Gel Pen Pack of 10','Cello Gel Pen Pack of 5'),
 ('books_stationery','Camlin Scientific Calculator','Camlin Scientific Calculator','Camlin Basic Calculator'),
 ('sports_fitness','Yonex Astrox 77 Pro Badminton Racket','Yonex Astrox 77 Pro Badminton Racket','Yonex Astrox 99 Pro Badminton Racket'),
 ('sports_fitness','Nivia Storm Football Size 5','Nivia Storm Football Size 5','Nivia Storm Football Size 4'),
 ('sports_fitness','Domyos 5kg Dumbbell','Domyos 5kg Cast Iron Dumbbell','Domyos 10kg Cast Iron Dumbbell'),
 ('sports_fitness','Cosco Tennis Balls Pack of 3','Cosco Tennis Balls Pack of 3','Cosco Tennis Balls Pack of 6'),
 ('sports_fitness','Adidas Football Shoes UK 9','Adidas Football Shoes UK 9','Adidas Football Shoes UK 8'),
 ('sports_fitness','Wilson Pro Staff 97 315g Racket','Wilson Pro Staff 97 315g Tennis Racket','Wilson Pro Staff 97 300g Tennis Racket'),
 ('furniture_home','Wakefit Queen Memory Foam Mattress 78x60 inches','Wakefit Queen Memory Foam Mattress 78x60 inches','Wakefit King Memory Foam Mattress 78x72 inches'),
 ('furniture_home','Nilkamal 4 Seater Dining Table','Nilkamal 4 Seater Dining Table','Nilkamal 6 Seater Dining Table'),
 ('furniture_home','Godrej 3 Door Wardrobe','Godrej 3 Door Wardrobe','Godrej 2 Door Wardrobe'),
 ('furniture_home','IKEA LACK Side Table','IKEA LACK Side Table','IKEA MICKE Computer Desk'),
 ('furniture_home','Durian Leather Sofa 3 Seater','Durian Leather Sofa 3 Seater','Durian Leather Sofa 2 Seater'),
 ('furniture_home','Philips 9W LED Ceiling Light','Philips 9W LED Ceiling Light','Philips 12W LED Ceiling Light'),
]


def evaluate():
    results=[]
    for i,(domain,query,yes,no) in enumerate(CASES):
        items=[{'name':name,'retailer':shop,'price':1000+i,'availability':'In Stock',
                'url':f'https://example.com/qa/novel-{i}-{j}'}
               for j,(name,shop) in enumerate(((yes,'Retailer A'),(no,'Retailer B')))]
        accepted=process_offers(query,items,domain=domain)
        passed={r['name'] for r in accepted}
        results.append({'domain':domain,'query':query,'positive':yes,'negative':no,
                        'positive_accepted':yes in passed,'negative_rejected':no not in passed})
    stats=Counter()
    for r in results:
        stats['positive_accepted']+=r['positive_accepted']
        stats['negative_rejected']+=r['negative_rejected']
    payload={'kind':'synthetic held-aside product matching tests','cases':len(results),
             'positive_passes':stats['positive_accepted'],'negative_passes':stats['negative_rejected'],
             'failures':[r for r in results if not(r['positive_accepted'] and r['negative_rejected'])],
             'all_cases':results}
    path=Path(__file__).resolve().parent.parent/'artifacts/search_models/novel_product_qa.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in payload.items() if k!='all_cases'},indent=2))
    return payload


if __name__=='__main__':
    evaluate()
