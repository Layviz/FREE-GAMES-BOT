import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime

steam_search_url = "https://store.steampowered.com/search?maxprice=free&category1=994%2C996%2C993%2C992%2C998&specials=1&ndl=1"

def fetch_free_steam_games():
    response = requests.get(steam_search_url)
    if response.status_code != 200:
        print("Failed to retrieve data from Steam.")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    game_elements = soup.find_all('a', class_='search_result_row')

    free_games = []
    for game in game_elements:
        title = game.find('span', class_='title').text
        link = game['href']
        # cut trailing parameters from link
        link = link.split('?')[0]
        free_games.append((title, link, "steam"))

    return free_games

def ensure_db():
    conn = sqlite3.connect('free_games.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS games
                 (title TEXT, link TEXT, platform TEXT, date_added INTEGER)''')
    conn.commit()
    conn.close()

def store_in_db(games):
    current_date = datetime.now()
    if current_date.hour < 19:
        current_date = current_date.replace(day=current_date.day - 1)
    current_date_int = current_date.year * 10000 + current_date.month * 100 + current_date.day
    games_with_date = [(title, link, platform, current_date_int) for title, link, platform in games]
    conn = sqlite3.connect('free_games.db')
    c = conn.cursor()

    #remove games that are no longer free, i.e. not in the current list
    c.execute('SELECT link FROM games') 
    existing_links = {row[0] for row in c.fetchall()}
    links_to_remove = existing_links - {link for _, link, _ in games}
    if links_to_remove:
        c.executemany('DELETE FROM games WHERE link = ?', [(link,) for link in links_to_remove])
        conn.commit()
    
    #Check for games already in the database to avoid duplicates
    c.execute('SELECT link FROM games')
    existing_links = {row[0] for row in c.fetchall()}
    games_to_insert = [game for game in games_with_date if game[1] not in existing_links]
    if games_to_insert:
        c.executemany('INSERT INTO games (title, link, date_added) VALUES (?, ?, ?)', games_with_date)
        conn.commit()
    conn.close()

def check_for_new_free_games(games):
    conn = sqlite3.connect('free_games.db')
    c = conn.cursor()
    c.execute('SELECT link FROM games')
    existing_links = {row[0] for row in c.fetchall()}
    conn.close()
    new_games = [game for game in games if game[1] not in existing_links]
    return new_games

def get_new_free_games():
    ensure_db()
    free_games = fetch_free_steam_games()
    new_games = check_for_new_free_games(free_games)
    store_in_db(free_games)
    return new_games

def get_steam_game_description(link):
    response = requests.get(link)
    if response.status_code != 200:
        return "Failed to retrieve game description."

    soup = BeautifulSoup(response.text, 'html.parser')
    desc_div = soup.find('div', class_='game_description_snippet')
    if desc_div:
        return desc_div.text.strip()
    return "No description available."

def get_steam_game_image(link):
    response = requests.get(link)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    img_div = soup.find('img', class_='game_header_image_full')
    if img_div:
        return img_div['src']
    return None
