import datetime
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import json
import smtplib
import ssl
links_file = "links.json"
news_file = "news.txt"
logs_file = "logs.txt"
wordpress_file = "wordpress_credentials.json"
mail_credentials_file = "mail_credentials.json"

def url_scrape(website_url: str, last_link: str):  # Finding the posts in given link.
    url_data = requests.get(website_url, headers={'User-Agent': 'Mozilla/5.0'})
    if url_data.status_code == 200:  # If the request fulfilled successfully continue
        soup = BeautifulSoup(url_data.text, 'html.parser')
        soup = soup.find("div", {"class": "ipb-grid ipb-grid--d-row"})
        links = [node.get('href') for node in soup.find_all("a")]
        if links[0] == last_link:  # If last link in list of posts is same as last scraped link
            return last_link  # Return last link

        info_scrape_status_code = info_scrape(links[0])
        if info_scrape_status_code == 200:  # If the post was scraped successfully,
            return str(links[0])  # return its link as last link that was scraped
        else:
            if info_scrape_status_code != 9001:  # Because logs for WP are handled separately they don't need to be logged
                log = ["Nie można było otworzyć strony z postem z informacjami."]
                file_write(log, logs_file, "a+")
            return last_link  # If the second request didn't finish successfully return last link to be saved.
    else:
        log = ["Nie można było otworzyć głównej listy z postami."]
        file_write(log, logs_file, "a+")
        return last_link  # If the first request didn't finish successfully return last link to be saved.


def info_scrape(website_url: str):
    url_data = requests.get(website_url, headers={'User-Agent': 'Mozilla/5.0'})
    if url_data.status_code == 200:
        news = BeautifulSoup(url_data.text, 'html.parser')
        title = news.select("h1",{"class": "entry-title"})
        post_title = " "
        for title_text in title:
            post_title = title_text.text

        news = news.find("div", {"class": "entry-content"})
        news_list = [item for item in news]
        wordpress_status_code = wordpress_publish(news_list, website_url, post_title)
        if wordpress_status_code == 201:  # If code is 201 it means it published successfully.
            file_write(news_list, news_file, 'a+')
            return url_data.status_code
        else:
            return 9001   # Returning code that will trigger fail condition. Doesn't matter which.
    else:
        return url_data.status_code


def json_write(list_of_data, filename: str, access_parameter: str):
    file = open(filename, access_parameter)
    json.dump(list_of_data, file, indent=4)


def file_write(list_of_data: list, filename: str, access_parameter: str):
    file = open(filename, access_parameter)
    if access_parameter == 'a+':
        file.write('\nDane z ' + str(datetime.now()) + '\n\n')
        for item in list_of_data:
            file.write(str(item).replace(u'\u202f', ' ') + '\n')
    else:
        for item in list_of_data:
            file.write(str(item).replace(u'\u202f', ' ') + '\n')
    file.close()


def json_read(filename: str):
    with open(filename, 'r', encoding='utf8') as openfile:
        json_object = json.load(openfile)
    return json_object


def wordpress_publish(content_list: list, source_link: str, post_title: str):
    wordpress_credentials = json_read(wordpress_file)
    wordpress_url = wordpress_credentials["wordpress_url"]
    username = wordpress_credentials["username"]
    password = wordpress_credentials["password"]
    content = ""

    for content_item in content_list:
        content = content + str(content_item).replace(u'\u202f', ' ') + '\n'

    content = content + '<p>Źródło informacji: <a href="' + source_link + '">Strona producenta</a>' + '</p>\n'

    data = {
        'title': post_title,
        'content': content,
        'status': 'draft'  # Use 'draft' to save the post as a draft
        # TODO Before deployment. Ask about categories
    }

    response = requests.post(wordpress_url, auth=(username, password), json=data)

    if response.status_code == 201:
        logs = ['Post created successfully']
        json_write(logs, logs_file, 'a+')
        send_email(source_link)
        return response.status_code  # Just to keep it consistent and 1 check in previous
    else:
        logs = ['Can\'t create a post. Response: ' + str(response.text)]
        file_write(logs, logs_file, 'a+')
        print('Failed to create post: ' + response.text)
        return response.status_code


def send_email(post_url: str):
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    email_credentials = json_read(mail_credentials_file)

    message = """\
Subject: Nowy post na stronie Enovy

Na stronie Enovy pojawil sie nowy post, zostal on dodany jako szkic do Wordpressa. 
Link do oryginalnego postu Enovy: """ + post_url

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(email_credentials["sender_email"], email_credentials["password"])

        server.sendmail(email_credentials["sender_email"], email_credentials["receiver_email"], message)


def main():
    enova_versions_url = "https://www.enova.pl/aktualnosci/nowe-wersje-systemu/"
    promotions_url = "https://www.enova.pl/aktualnosci/promocje/"
    links_to_scrape = [enova_versions_url,  promotions_url]  # Add or remove from here if it's meant to be skipped
    links_to_write = json_read(links_file)

    for link in links_to_scrape:
        links_to_write[link]["url"] = url_scrape(link, links_to_write[link]["url"])
    json_write(links_to_write, links_file, 'w')


main()
