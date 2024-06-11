import asyncio
import datetime
import json
import logging
import os
import re
import sqlite3
from datetime import datetime
from time import sleep

import requests
import tqdm
from bs4 import BeautifulSoup
from newspaper import Article

# Ensure the script uses the correct working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(current_dir, '../data')

logger = logging.getLogger(__name__)
logging.basicConfig(filename=os.path.join(
    data_dir, 'scraper.log'), level=logging.INFO)
now = datetime.now()
logger.info('Started scraper at {}'.format(now.strftime("%H:%M:%S %d/%m/%Y")))

num_pages_to_scrape = 1
base_url = "https://n1info.hr/wp-json/wp/v2/uc-all-posts"
params = {
    'per_page': 10
}


def save_to_database(article_list):
    connection = sqlite3.connect(os.path.join(data_dir, 'articles.db'))
    cursor = connection.cursor()

    try:
        sqlite_insert_query = """INSERT INTO articles (article_id, title, date, time, hashtags, text, source, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        records_to_insert = [(article.article_id, article.title, article.date, article.time,
                              json.dumps(article.hashtags), article.text, article.source, article.category) for article in article_list]

        cursor.executemany(sqlite_insert_query, records_to_insert)
        connection.commit()
    except sqlite3.Error as error:
        logger.error(f"Failed to insert records into articles table: {error}")
    finally:
        cursor.close()
        connection.close()


class N1Article:
    def __init__(self, article_id="", title="", date="", time="", hashtags=None, text="", source="n1", category=""):
        self.article_id = article_id
        self.title = title
        self.date = date
        self.time = time
        self.hashtags = hashtags if hashtags is not None else []
        self.text = text
        self.source = source
        self.category = category

    def to_dict(self):
        return {
            "article_id": self.article_id,
            "title": self.title,
            "date": self.date,
            "time": self.time,
            "hashtags": self.hashtags,
            "text": self.text,
            "source": self.source,
            "category": self.category
        }

    def __str__(self):
        return f"Article ID: {self.article_id}\nTitle: {self.title}\nDate: {self.date}\nTime: {self.time}\nHashtags:  {self.hashtags}\nText: {self.text}\nSource: {self.source}\nCategory: {self.category}"


def load_last_scraped_datetime():
    try:
        with open(os.path.join(data_dir, 'last_scraped_datetime.txt'), "r") as file:
            datetime_str = file.read().strip()
            return datetime.fromisoformat(datetime_str)
    except FileNotFoundError:
        return None


def save_last_scraped_datetime(last_scraped_datetime):
    try:
        with open(os.path.join(data_dir, 'last_scraped_datetime.txt'), "w") as file:
            file.write(last_scraped_datetime.isoformat())
        logger.info("Last scraped datetime saved successfully.")
    except Exception as e:
        logger.info("Error saving last scraped datetime:", e)


def create_directory_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def collect_articles_from_api(base_url, params, last_scraped_datetime):
    articles_list = []
    page_number = 1
    should_stop = False

    while not should_stop:
        params['page'] = page_number
        logger.info(f"Fetching articles from page {page_number}...")
        logger.info(f"API URL: {base_url}, Parameters: {params}")
        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            data = response.json()
            if not data:  # No more articles available
                logger.info("No more articles available.")
                break

            for article_data in data['data']:
                article_datetime = datetime.strptime(
                    article_data.get('date_unparsed', ''), "%Y-%m-%d %H:%M:%S")
                if last_scraped_datetime and article_datetime <= last_scraped_datetime:
                    should_stop = True
                    logger.info(
                        "Stopping the loop as article datetime is older than or equal to last scraped datetime.")
                    break

                article_id = str(article_data.get('id', ''))
                title = article_data.get('title', '')
                date = article_datetime.strftime("%Y-%m-%d")
                time = article_datetime.strftime("%H:%M")
                category = article_data.get('category_name', '')
                link = article_data.get('link', '')

                article = N1Article(article_id=article_id, title=title,
                                    date=date, time=time, source=link, category=category)
                articles_list.append(article)

        else:
            logger.error(
                f"Failed to fetch page {page_number}: Status code {response.status_code}")
        page_number += 1

    return articles_list


def get_text_from_article(article_source):
    try:
        # Using article object to parse the page content
        article = Article(article_source, language="hr")
        article.download()
        article.parse()
        text = article.text

        # Processing the text so that it leaves only raw data
        modified_text = text.replace(
            'N1 pratite putem aplikacija za Android | iPhone/iPad i mreža Twitter | Facebook | Instagram | TikTok.', '')
        modified_text = modified_text.replace('Podijeli :', '')
        modified_text = modified_text.replace('\n', ' ')
        pattern = r'\b\S+\s?\S*\/\S+\b'
        modified_text = re.sub(pattern, '', modified_text)
        pattern = r'\b[\w\s]+\s?\/\s?\w+\b'
        modified_text = re.sub(pattern, '', modified_text)
        pattern = r'\b.+?\s?\/\s?.+?\b'
        modified_text = re.sub(pattern, '', modified_text)
        pattern = r'\b\w+\s+via\s+REUTERS\b'
        modified_text = re.sub(pattern, '', modified_text)
        modified_text = modified_text.replace('Pexels', '')
        modified_text = modified_text.replace('N1', '')
        modified_text = modified_text.replace('via REUTERS', '')
        modified_text = modified_text.replace('/', '')
        modified_text = modified_text.lstrip()
        return modified_text
    except Exception as e:
        logger.error(f"Error occurred while parsing article: {e}")
        return ""


def get_tags_from_article(article_source):
    response = requests.get(article_source, headers={
                            'Accept-Charset': 'UTF-8'})
    content = response.content.decode('utf-8')
    soup = BeautifulSoup(content, 'html.parser')
    tags_elements = soup.find_all(rel="tag")
    tags = [element.get_text() for element in tags_elements]
    return tags


def scrape_each_article(article_list):
    for article in tqdm.tqdm(article_list, desc="Scraping Articles"):
        article_source = article.source
        text = get_text_from_article(article_source)
        tags = get_tags_from_article(article_source)
        article.text = text
        article.hashtags = tags


def load_ids():
    connection = sqlite3.connect(os.path.join(data_dir, 'articles.db'))
    cursor = connection.cursor()
    try:
        query = "SELECT article_id FROM articles"
        cursor.execute(query)
        rows = cursor.fetchall()
        id_dict = {}
        for row in rows:
            article_id = row[0]
            id_dict[article_id] = None
        # If the database is empty, initialize with article IDs from the API
        if not id_dict:
            for article in article_list:
                id_dict[article.article_id] = None
        return id_dict
    finally:
        cursor.close()
        connection.close()


try:
    with open(os.path.join(data_dir, 'duplicates.json'), 'r') as file:
        duplicates = json.load(file)
except:
    duplicates = {}

last_scraped_datetime = load_last_scraped_datetime()

print("Starting scraper...                                   ", end="\r")

article_list = collect_articles_from_api(
    base_url, params, last_scraped_datetime)

ids = load_ids()

for article in article_list:
    if article.article_id in ids:
        if article.article_id in duplicates:
            counter = duplicates[article.article_id] + 1
            article.article_id += ("-" + str(counter))
            a_id = article.article_id.split("-")[0]
            duplicates[a_id] = counter
        else:
            duplicates[article.article_id] = 1
            article.article_id += "-1"

try:
    with open(os.path.join(data_dir, 'duplicates.json'), 'w') as file:
        json.dump(duplicates, file, ensure_ascii=False, indent=4)
    logger.info(
        "Duplicates data has been successfully written to 'duplicates.json'.")
except Exception as e:
    logger.info(f"An error occurred while writing to 'duplicates.json': {e}")

if article_list:
    last_article_datetime = article_list[0].date + " " + article_list[0].time
    save_last_scraped_datetime(datetime.strptime(
        last_article_datetime, "%Y-%m-%d %H:%M"))

    logger.info("Processing and saving the scraped articles...")
    scrape_each_article(article_list)
    save_to_database(article_list)
    for article in tqdm.tqdm(article_list, desc="Saving to directory..."):
        if article.text != "" and article.category != "N1 Studio uživo":
            directory = os.path.join(data_dir, '../data_temp', article.date)
            create_directory_if_not_exists(directory)
            file_name = f"{article.article_id}.json"
            file_path = os.path.join(directory, file_name)
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(article.to_dict(), file,
                          ensure_ascii=False, indent=4)
    logger.info("Articles data successfully written to JSON file.")
else:
    logger.info("No articles fetched from the API.")
