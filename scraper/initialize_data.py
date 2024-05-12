import datetime
import logging
import os
import shutil
import sqlite3
import subprocess
import sys


def save_last_scraped_datetime(last_scraped_datetime):
    try:
        with open("../data/last_scraped_datetime.txt", "w") as file:
            file.write(last_scraped_datetime.isoformat())
        logger.info("Last scraped datetime saved successfully.")
    except Exception as e:
        logger.error("Error saving last scraped datetime:", e)


# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(filename='../data/scraper.log', level=logging.INFO)

logger.info("Initiated setup at {} {}".format(
    datetime.datetime.now().time(), datetime.datetime.now().date()))

# Remove the data_temp directory and its subitems if it exists
data_temp_dir = '../data_temp'
if os.path.exists(data_temp_dir):
    shutil.rmtree(data_temp_dir)
    logger.info("Deleted 'data_temp' directory and its subitems")


# Establish connection to the database
connection = sqlite3.connect('../data/articles.db')
cursor = connection.cursor()

try:
    cursor.execute("DROP TABLE IF EXISTS articles")
    connection.commit()
    logger.info("Table 'articles' is dropped")
except sqlite3.Error as error:
    logger.error(f"Failed to drop articles table: {error}")


try:
    sqlite_create_table_query = """CREATE TABLE IF NOT EXISTS articles (
            article_id TEXT PRIMARY KEY, -- No AUTOINCREMENT
            title TEXT,
            date DATE,
            time TIME,
            hashtags TEXT,
            text TEXT,
            source TEXT,
            category TEXT
        )"""
    logger.info("Table 'articles' is created")
    cursor.execute(sqlite_create_table_query)
    connection.commit()
except sqlite3.Error as error:
    logger.error(f"Failed to drop articles table: {error}")

if connection:
    cursor.close()
    connection.close()

# Save last scraped datetime
current_datetime = datetime.datetime.now()
previous_two_days_datetime = current_datetime - \
    datetime.timedelta(days=2)
last_scraped_datetime = previous_two_days_datetime
logger.info(datetime.datetime.isoformat(last_scraped_datetime))
save_last_scraped_datetime(last_scraped_datetime)

file_path = '../data/duplicates.json'

with open(file_path, 'w') as file:
    file.truncate(0)

# Run scraper
python_executable = sys.executable
print("This may take a few minutes...", end="\r")
subprocess.run([python_executable, 'n1_scraper.py'])
print("Finished!", end="\r")
