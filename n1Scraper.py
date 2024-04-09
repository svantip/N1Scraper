import os
import datetime
from bs4 import BeautifulSoup
import requests
from newspaper import Article
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(filename='scraper.log', level=logging.INFO)
now = datetime.now()
logger.info('Started scraper at {}'.format(now.strftime("%H:%M:%S %d/%m/%Y")))

num_pages_to_scrape = 1
base_url = "https://n1info.hr/wp-json/wp/v2/uc-all-posts"
params = {
    'per_page': 10
}


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
        with open("last_scraped_datetime.txt", "r") as file:
            last_scraped_datetime_str = file.read().strip()
            return datetime.datetime.fromisoformat(last_scraped_datetime_str)
    except FileNotFoundError:
        return None


def save_last_scraped_datetime(last_scraped_datetime):
    with open("last_scraped_datetime.txt", "w") as file:
        file.write(last_scraped_datetime.isoformat())


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
            if not data:
                logger.info("No more articles available.")
                break

            for article_data in data['data']:
                article_datetime = datetime.datetime.strptime(
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
    article = Article(article_source, language="hr")
    article.download()
    article.parse()
    text = article.text

    modified_text = text.replace(
        'N1 pratite putem aplikacija za Android | iPhone/iPad i mreža Twitter | Facebook | Instagram | TikTok.', '')
    modified_text = modified_text.replace('Podijeli :', '')
    modified_text = modified_text.replace('\n', ' ')
    return modified_text


def get_tags_from_article(article_source):
    response = requests.get(article_source, headers={
                            'Accept-Charset': 'UTF-8'})
    content = response.content.decode('utf-8')
    soup = BeautifulSoup(content, 'html.parser')
    tags_elements = soup.find_all(rel="tag")
    tags = [element.get_text() for element in tags_elements]
    return tags


def scrape_each_article(article_list):
    for article in article_list:
        article_source = article.source
        text = get_text_from_article(article_source)
        tags = get_tags_from_article(article_source)
        article.text = text
        article.hashtags = tags


last_scraped_datetime = load_last_scraped_datetime()

article_list = collect_articles_from_api(
    base_url, params, last_scraped_datetime)

if article_list:
    logger.info("Processing and saving the scraped articles...")
    scrape_each_article(article_list)
    for article in article_list:
        directory = os.path.join("data", article.date)
        create_directory_if_not_exists(directory)
        file_name = f"{article.article_id}.json"
        file_path = os.path.join(directory, file_name)
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(article.to_dict(), file, ensure_ascii=False, indent=4)

    last_article_datetime = article_list[0].date + " " + article_list[0].time
    save_last_scraped_datetime(datetime.datetime.strptime(
        last_article_datetime, "%Y-%m-%d %H:%M"))

logger.info("Articles data successfully written to JSON files.")
