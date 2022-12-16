from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

import requests
from bs4 import BeautifulSoup

import time
import datetime as dt
import pandas as pd

def scroll_page(driver, y=4000, y_step=4000, duration_limit=600, sleep=2.5):
    # y = initial height to scroll to
    # y_step = incremental step to scroll 
    # duration_limit = seconds the process will run for 
    # sleep = duration process will stall inbetween scrolls 
    duration = 0
    start_time = dt.datetime.now()
    while duration < duration_limit: # When duration exceeds the limit, process ends
        driver.execute_script(f'window.scrollTo(0, {y})')
        time.sleep(sleep)
        current_time =  dt.datetime.now()
        duration = (current_time - start_time).seconds
        y += y_step
     
def scrape_review_data(review_object): 
    # review_object = web element corresponding to an album review thumbnail

    # Core Review Data (titles, artists, links, etc.)
    core_review_data = review_object.find_element(By.TAG_NAME, 'a')    
    review_title_data = core_review_data.find_element(By.XPATH, 'div[2]')
    artists = ' / '.join([e.text for e in review_title_data.find_elements(By.TAG_NAME, 'li')])                            
    album_title = review_title_data.find_element(By.TAG_NAME, 'h2').text
    review_link = core_review_data.get_attribute('href')
    
    # Meta Review Data (authors, 'best new' designation, genres, publish date)
    review_meta_data = review_object.find_element(By.XPATH, 'div')
    if len(review_meta_data.find_elements(By.TAG_NAME, 'ul'))==2:
        genres = ' / '.join([e.text for e in review_meta_data.find_element(By.XPATH, 'ul[1]').find_elements(By.TAG_NAME, 'li')])
        authors = ' / '.join([e.text.replace('BY: ', '') for e in review_meta_data.find_element(By.XPATH, 'ul[2]').find_elements(By.TAG_NAME, 'li')])
    else:    
        genres = None
        authors = ' / '.join([e.text.replace('BY: ', '') for e in review_meta_data.find_element(By.XPATH, 'ul').find_elements(By.TAG_NAME, 'li')])
    best_new = 1 if review_meta_data.find_elements(By.CLASS_NAME, 'review__meta-bnm') else 0
    publish_datetime = review_meta_data.find_element(By.TAG_NAME, 'time').get_attribute('datetime')
    
    return album_title, artists, genres, authors, best_new, publish_datetime, review_link
        
def scrape_review_article(url):
    # Function takes a link to a review and returns the article text, as well as the review score
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    try: 
        score = float(soup.find('div', {'class': 'ScoreBoxWrapper-cqxrzg hvtCii'}).find('p').get_text())
    except AttributeError: 
        score = float(soup.find('span', {'class': 'score'}).get_text())
    article_body = soup.find('div', {'class': 'ArticlePageChunks-lgZRyR kfMxne'})
    if not article_body: article_body = soup.find('div', {'class': 'contents dropcap'})
    article = ' '.join([p.get_text() for p in article_body.find_all('p')]).strip()
    return article, score

       
options = Options()
options.add_argument('--headless')
chromedriver_path = '/Users/benepstein/Desktop/pitchfork/chromedriver'
driver = webdriver.Chrome(chromedriver_path, options=options)

driver.get('https://pitchfork.com/reviews/albums/')
scroll_page(driver)
review_objects = driver.find_elements(By.CLASS_NAME, 'review')

reviews = pd.DataFrame()
for review_object in review_objects:
    album_title, artists, genres, authors, best_new, publish_datetime, review_link = scrape_review_data(review_object)
    review = pd.DataFrame({
        'album_title': album_title,
        'artists': artists,
        'genres': genres,
        'authors': authors,
        'best_new': best_new,
        'publish_datetime': publish_datetime,
        'review_link': review_link
        }, index=[0]) 
    reviews = pd.concat([reviews, review], axis=0).reset_index(drop=True)

#driver.quit()

while True:
    try: 
        for url in reviews[reviews['article'].isna()]['review_link']:
            reviews.loc[reviews['review_link']==url, ['article', 'score']] = scrape_review_article(url)
        break
    except ConnectionError:
        pass
        
reviews.to_csv('data/reviews.csv', index=False) 