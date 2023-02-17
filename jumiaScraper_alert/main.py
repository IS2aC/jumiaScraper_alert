from pymongo import MongoClient
from jumia_bot import JumiaBot
from flask import Flask, render_template, request

client = MongoClient('localhost', 27017)
app = Flask(__name__)


@app.route('/')
def welcome():
    return render_template('welcome.html')


@app.route('/connect_to_scrap', methods=['GET', 'POST'])
def connect_to_scrap():
    return render_template('product_to_scrap.html')


@app.route('/traitement', methods=['POST'])
def treatment():
    url = request.form.get("url")

    # Insertion de l'URL
    client['jumiaDB']["product_urls"].insert_one({"url": url})

    # Lancement du JumiaBot pour la recolte des informations sur le produit 
    bot = JumiaBot(mongodb_client=client)
    bot.scrap_urls()
    return render_template("treatment.html")


if __name__ == "__main__":
    app.run(debug=True)
