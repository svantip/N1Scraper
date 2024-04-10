import datetime
import logging
import subprocess
import sys

import psycopg2


def save_last_scraped_datetime(last_scraped_datetime):
    try:
        with open("last_scraped_datetime.txt", "w") as file:
            file.write(last_scraped_datetime.isoformat())
        logger.info("Last scraped datetime saved successfully.")
    except Exception as e:
        logger.info("Error saving last scraped datetime:", e)


logger = logging.getLogger(__name__)
logging.basicConfig(filename='scraper.log', level=logging.INFO)

logger.info("Initiated setup at {} {}".format(
    datetime.datetime.now().time(), datetime.datetime.now().date()))

current_datetime = datetime.datetime.now()
previous_two_days_datetime = current_datetime - datetime.timedelta(days=2)
last_scraped_datetime = previous_two_days_datetime
logger.info(datetime.datetime.isoformat(last_scraped_datetime))
save_last_scraped_datetime(last_scraped_datetime)

connection = psycopg2.connect(user="svan1233",
                              password="tockica184",
                              host="localhost",
                              port="5432",
                              database="N1articles")

try:
    cursor = connection.cursor()
    postgres_createtable_query = """CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    title TEXT,
    date DATE,
    time TIME,
    hashtags TEXT[],
    text TEXT,
    source TEXT,
    category TEXT
    ) """
    cursor.execute(postgres_createtable_query)
    connection.commit()
    logger.info(
        "Table articles is created")
except (Exception, psycopg2.Error) as error:
    logger.error(
        f"Failed to insert record into articles table: {error}")
finally:
    if connection:
        cursor.close()
        connection.close()

python_executable = sys.executable

print("This may take a few minutes...")
subprocess.run([python_executable, 'n1Scraper.py'])
print("Finished!", end="\r")
