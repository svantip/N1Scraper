import os
import shutil

import psycopg2


def delete_folders():
    data_folder = 'data'
    for folder in os.listdir(data_folder):
        folder_path = os.path.join(data_folder, folder)
        if os.path.isdir(folder_path):
            try:
                shutil.rmtree(folder_path)
                print(f"Deleted folder: {folder_path}")
            except OSError as e:
                print(f"Error: {folder_path} : {e.strerror}")


def delete_log():
    with open('scraper.log', 'w') as file:
        file.write('')
    print("Deleted the logs")


def delete_articles_from_database():
    try:
        connection = psycopg2.connect(user="svan1233",
                                      password="tockica184",
                                      host="localhost",
                                      port="5432",
                                      database="N1articles")
        cursor = connection.cursor()
        delete_query = "DELETE FROM articles;"
        cursor.execute(delete_query)
        connection.commit()
        print("All records deleted from the 'articles' table.")
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL:", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed.")


file_path = '../data/duplicates.json'

with open(file_path, 'w') as file:
    file.truncate(0)

delete_folders()
delete_articles_from_database()
delete_log()
