import requests
import os
from datetime import datetime
from bs4 import BeautifulSoup

#Request for a url using Scrape.API
def get_request(url, asin, seller_id=None):
    payload = {'api_key': "39c9d63b8d4abb7fb6478c011ea3c72a", 'url': url}
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, sdch, br",
        "Accept-Language": "en-US,en;q=0.8",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
    }
    count = 0
    max_tries = 3
    #catches errors, and triees to reconnect up to a max of two more times
    while count < max_tries:
        try:
            r = requests.get('http://api.scraperapi.com', params=payload, headers=headers, timeout=10)
            if r.status_code != 200: #checks if it is actually HTML
                count = count + 1
            else:
                count = max_tries
                downloadHTML(asin=asin, seller_id=seller_id, response_text=r.text)
                return r.text
        except requests.ConnectionError as e: #catches a connection error
            count = count + 1
            print('Connection Error, tries: ',count)
        except requests.Timeout as e: #catches a timeout error
            count = count + 1
            print('Timeout Error, tries: ',count)

#Method that parses the html to find the names of the sellers of a certain ASIN, their id,
#the price at which they are selling at, and whether or not they are FBA,
# SFP, or FBM.
def parse_seller_id(response, ASIN, results_list=[]):
    soup = BeautifulSoup(response, 'lxml')

    for element in soup.find_all('div', class_='a-row a-spacing-mini olpOffer'): #looping through the rows of the table that has the merchants
       #setting the variable names for the dictionary
        seller_id = ''
        fulfillment_method = ''
        seller_name = ''
        price = ''
        if element.find('h3', class_='a-spacing-none olpSellerName').a:
            seller_url = element.h3.a.get('href')  # finding the product url from a specific seller
            seller_id = seller_url[seller_url.find('seller=') + 7:]  # finding the seller id from the seller url
            print(seller_id)
            if element.find('div',
                            class_='a-column a-span2 olpPriceColumn').i:  # finding if the seller has a prime badge
                if seller_url[seller_url.find('isAmazonFulfilled=') + 18:seller_url.find(
                        'isAmazonFulfilled=') + 19] == '1':  # If url has "isAmazonFulfilled=1", then the seller is "FBA" or "fulfilled by Amazon"
                    print('FBA')
                    fulfillment_method = 'FBA'
                else:  # otherwise, the seller is "SFP" or "seller fulfilled prime"
                    print("SFP")
                    fulfillment_method = 'SFP'
            else:  # If the seller doesn't have a prime badge, then it is "FBM" or "fulfilled by merchant"
                print('FBM')
                fulfillment_method = 'FBM'
            print(element.h3.a.text) #getting the seller name
            seller_name = element.h3.a.text
            #print(element.span.text.strip())
            price = element.span.text.strip() #getting the price
            if price == '': #checking to see if there is a price; if not, set to a default of zero
                price = 0.0
            else: #if there is a price, convert the string to a float
                price = float(price[1:])
            print(price)
        else: #if the merchant is amazon
            seller_id = 'A14X08UWVFHIJJ' #default amazon seller ID
            print(seller_id)
            print("sold by Amazon")
            fulfillment_method = "sold by Amazon"
            print("Amazon")
            seller_name = "Amazon"
            price = element.span.text.strip()
            if price == '':
                price = 0.0
            else:
                price = float(price[1:])
            print(price)
        #initiating the dictionary
        output_dict = {'asin': ASIN, 'seller_id': seller_id, 'seller_name': seller_name, 'price': price, 'fulfillment_method': fulfillment_method}
        previous = next((item for item in results_list if item['seller_id'] == seller_id), None) #checking to see if seller ID has already appeared
        if previous is None:
            results_list.append(output_dict)
        else:
            if previous['price'] <= price:
                continue
            elif previous['price'] == 0.0:
                results_list = [d for d in results_list if d.get('seller_id') != seller_id]
                results_list.append(output_dict)
            else:
                results_list = [d for d in results_list if d.get('seller_id') != seller_id]
                results_list.append(output_dict)

    return results_list



#Method that parses the html to find the inventory of a certain ASIN from a certain merchant
def parse_inventory(response):
    soup = BeautifulSoup(response, 'lxml')
    #for x in urls:
       #soup = BeautifulSoup(response, 'lxml')
    #finding the text above the drop down menu
    availability = soup.find('div', id='availability').span.text

    #if no text, then it is out of stock
    if not availability:
        qty = 0
    #else, if text is "Only 'number' left in stock - order soon" find the number
    elif not availability.find('Only ') == -1:
        qty = availability[availability.find('Only ')+5:availability.find(' left')]
    #else if there is text, find that text
    elif availability.find('Only ') == -1 and not availability.find('In stock on') == -1:
        qty = availability.strip()
    #else, check the dropdown menu and find the last number(#in stock)
    elif not soup.find_all('select', id='quantity') == []:
        for element in (soup.find_all('select', id='quantity')):
            qty = element.find_all('option')[-1].text
    else:
        qty = 'error'
    print(qty)

def check_pages(response):
    check = False
    soup = BeautifulSoup(response, 'lxml')
    pages_exist = not(soup.find_all('ul', class_='a-pagination') == [])
    if pages_exist:
        for element in (soup.find_all('ul', class_='a-pagination')):
            if element.find('li', class_='a-last'):
                if element.find('li', class_='a-disabled a-last'):
                    check = False
                else:
                    check = True

    return check

def get_nextpage_url(response):
    soup = BeautifulSoup(response, 'lxml')
    link = ''
    for element in (soup.find_all('ul', class_='a-pagination')):
        link = link + ('www.amazon.com' + element.find('li', class_='a-last').a.get('href'))
    return link

def get_sellers_url(ASIN):
    sellers_url_array = []
    sellers_url = 'https://www.amazon.com/gp/offer-listing/' + ASIN + '/ref=olp_f_new?ie=UTF8&f_new=true'
    sellers_url_array.append(sellers_url)
    return sellers_url_array

def get_product_seller_url(ASIN, seller_id):
    product_seller_url = 'https://www.amazon.com/dp/' + ASIN + '/ref=sr_1_2?m=' + seller_id + '&th=1&psc=1'
    return product_seller_url

def parse_urls(ASIN):
    sellers_url = get_sellers_url(ASIN)
    seller_ids = []
    sellers_response = get_request(url=sellers_url, asin=ASIN)
    for d in (parse_seller_id(sellers_response, ASIN)):
        seller_ids.append(d['seller_id'])
    seller_ids = (parse_seller_id(sellers_response, ASIN))
    while check_pages(sellers_response):
        next_url = get_nextpage_url(sellers_response)
        sellers_response = get_request(url=next_url, asin=ASIN)
        seller_ids = (parse_seller_id(sellers_response,ASIN, seller_ids))
    # for seller_id in seller_ids:
    #     product_url = get_product_seller_url(ASIN, seller_id)
    #     product_response = get_request(url=product_url, asin=ASIN, seller_id=seller_id)
    #     parse_inventory(product_response)
    print(seller_ids)



#r1 =open('/Users/jerrywu/PycharmProjects/test/HTML Texts/2019-08-01_B0713WFVDV.txt','r').read()
#print(check_pages(r1))
#print(parse_seller_id(r1,'B0713WFVDV'))
#parse_inventory(r1)

#function that downloads the HTML from a url
def downloadHTML(asin, seller_id, response_text):
    current_date = datetime.today().strftime('%Y-%m-%d')
    if seller_id:
        dest = os.path.join('HTML Texts', current_date+'_'+asin+'_'+seller_id+'.txt')
    else:
        dest = os.path.join('HTML Texts', current_date + '_' + asin + '.txt')
    file = open(dest, 'w')
    file.write(response_text)
    file.close()

parse_urls('B07GDFTSPV')



#response = get_request('https://www.amazon.com/gp/offer-listing/B07GDFTSPV/ref=olp_page_next?ie=UTF8&f_all=true&f_new=true&startIndex=10', 'B07GDFTSPV')
#file=open("2019-08-01_B07GDFTSPV_GoProPages.txt", 'w')
#file.write(response)
#file.close()
