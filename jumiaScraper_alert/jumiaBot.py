import os, re
import datetime
from bs4 import BeautifulSoup
import requests
from email.message import EmailMessage
import ssl
import smtplib


###### Envoie de mail ############
em =  EmailMessage()
def alert_email(sender, receiver, subject, pwd, percent, product, url):
    """ Fonction pour l'alerte  via email """

    percent = 100 - percent
    if percent < 0 :
        body = """
        Alerte smtp !!
        hausse de prix estimé a environ de: {}%
        sur le produit : {}...


        lien jumia : {}
        """.format(percent, product, url)
    else:
        body = """
        Alerte smtp !!
        Rabais de prix sur le produit de: {}%
        sur le produit : {}...


        lien jumia : {}
        """.format(percent, product, url)

    em['From'] = sender
    em['to'] = receiver
    em['Subject'] = subject
    em.set_content(body)
    context =  ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context =  context) as smtp:
        smtp.login(sender, password=pwd)
        smtp.sendmail(sender, receiver, em.as_string())


###### parametres email pour les envoies et recepetion ##########
send  = os.getenv('SENDER_EMAIL')
rec =  os.getenv('RECEIVER_EMAIL')
password_app = os.getenv('PWD')


##### class JUMIA BOT #############
class JumiaBot:
    def __init__(self, mongodb_client):
        self.mongodb_client = mongodb_client
        
    def get_product_data(self, product_url):
        r = requests.get(product_url)
        s =  BeautifulSoup(r.content, 'html.parser')
        title =  self.get_product_title(soup = s)
        rating = self.get_product_rating(soup = s)
        price =  self.get_product_price(soup =  s)
        return {
            "url":product_url,
            "title":title,
            "rate":rating,
            "price":eval(re.split(",| ",price)[0] + re.split(",| ",price)[1]),
            "date": datetime.datetime.now()
        }
        
    def get_product_title(self, soup):
        """ recuperation de l'intitulé du produit """

        try:
            return soup.find('h1',{'class':'-fs20 -pts -pbxs'}).get_text()
        except:
            return None
    
    def get_product_rating(self, soup):
        """ recuperation de la note accordé au produit par la communauté de consommateur """

        try:
            return int(soup.find('div', {'class':'stars _s _al'}).get_text().split(" ")[0])
        except:
            return None
        

    def get_product_price(slef, soup):
        """ recuperation du prix du produit """
        try:
            return soup.find('span', {'class':'-b -ltr -tal -fs24'}).get_text()
        except:
            return None

    #scraper un groupe de url presents dans la collections products_urls de la BD jumiaDB
    def scrap_urls(self):
        """ recuperation des informations definient ci-dessus  pour les données inserés dans la collection mongo """

        product_urls  =  self.mongodb_client['jumiaDB']['product_urls'].find()
        for product_url in product_urls:
            data =  self.get_product_data(product_url["url"])

            #insertion des données -- type upsert
            self.mongodb_client['jumiaDB']['product_data'].update_one({"url":data['url']},{"$set":data}, upsert = True)
            
            #creation implicite de la collection product_prices -- recuperation du dernier prix du produit
            try:
                last_product_price = self.mongodb_client['jumiaDB']['product_prices'].find({"url":data['url']}).sort([('created_at', -1)]).next()
            except:
                last_product_price =  None
                

            # insertion si le dernier prix du produit est inexistant ou pas     
            if last_product_price is None:
                self.mongodb_client['jumiaDB']['product_prices'].insert_one({
                    'url':product_url['url'],
                    "price":data["price"],
                    "created_at":datetime.datetime.now()                                             
                })

            elif last_product_price is not None and last_product_price['price'] != data['price']:
                self.mongodb_client['jumiaDB']['product_prices'].insert_one({
                    'url':product_url['url'],
                    "price":data["price"],
                    "created_at":datetime.datetime.now()      
                })
                
                #puisque le nom du produit et son prix  sont déjà existant dans la collection de suivit des produits -- evaluons le poucentages de hausse ou de baisse de prix
                percent =  round(100 - (last_product_price['price']*100/data['price']),2)

                #recuperation du nom du produit pour l'alerte SMTP
                name_product =  data['title']

                #URL jumia du produit
                url = data['url']


                #lancement de l'alerte mail
                alert_email(sender =  send, 
                            receiver = rec, 
                            subject = "ALERTE DE PRIX SMTP", 
                            pwd = password_app, 
                            percent = percent,
                            product= name_product,
                            url= url)

            