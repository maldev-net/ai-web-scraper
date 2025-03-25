import requests
from bs4 import BeautifulSoup
import re
import csv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import urllib.parse
import sys

username = "m03757629"
password = "Affan92(@$"
encoded_password = urllib.parse.quote_plus(password)
uri = f"mongodb+srv://{username}:{encoded_password}@cluster0.n4mps.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
    print('Failed to connect to MongoDB. Exiting...')
    sys.exit(1)

response = requests.get('https://www.daraz.pk/#?')

soup = BeautifulSoup(response.text, 'html.parser')

def extract_phone_numbers(text):
    phone_pattern = re.compile(r'\+?\d[\d -]{8,}\d')
    return phone_pattern.findall(text)

def extract_emails(text):
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    return email_pattern.findall(text)

page_text = soup.get_text()
phone_numbers = extract_phone_numbers(page_text)
emails = extract_emails(page_text)

all_links = soup.find_all('a')
urls = [link.get('href') for link in all_links if link.get('href')]

meta_description = soup.find('meta', {'name': 'description'})
description = meta_description['content'] if meta_description else "No description found"

social_media_links = [url for url in urls if any(sm in url for sm in ['facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com'])]

print('Phone Numbers:', phone_numbers)
print('Emails:', emails)
print('URLs:', urls)
print('Social Media Links:', social_media_links)
print('Description:', description)

data_to_store = {
    'Phone_Numbers': phone_numbers,
    'Emails': emails,
    'URLs': urls,
    'Social_Media_Links': social_media_links,
    'Description': description
}

csv_file = 'scraped_data.csv'

with open(csv_file, 'w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=data_to_store.keys())
    writer.writeheader()
    writer.writerow(data_to_store)

print('Data saved to CSV file:', csv_file)

try:
    db = client['scraping_db']
    collection = db['scraped_data']
    for record in collection.find():
        print(record)
    collection.insert_one(data_to_store)
    print('Data saved to MongoDB collection: scraped_data')
except Exception as e:
    print('Error:', e)
    print('Failed to insert data into MongoDB. Exiting...')
    sys.exit(1)
