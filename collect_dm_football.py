from bs4 import BeautifulSoup
import urllib
# import re, urlparse # for utf-8 html url error handling
import re
import urllib.parse
import os
import errno
from summa import summarizer

OUTPUT_FILE_NAME = 'out.text'
URL_TARGET = "https://www.dailymail.co.uk/home/search.html?offset="
URL_TYPE = "&size="
URL_REST = "&sel=site&searchPhrase=&sort=recent&channel=football&type=article&type=video&type=permabox&days=all"
# offset goes up with 10s

output_dir = "./dm_data/"

def urlEncode(url) :
    url = urllib.parse.urlsplit(url)
    url = list(url)
    url_list_len = len(url)

    for list_idx in range(url_list_len):
        url[list_idx] = urllib.parse.quote(url[list_idx])
    
    url = urllib.parse.urlunsplit(url)
    return url


def make_dir(dir):
    if not os.path.exists(os.path.dirname(dir)):
        try:
            os.makedirs(os.path.dirname(dir))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise


def try_save_data_with_thinCenter_from(url, count):
    print("starting save_data_from func")
    url = urlEncode(url)
    try:
        web_source = urllib.request.urlopen(url)
    except:
        print("bad url : not found...")
        return False

    soup = BeautifulSoup(web_source, 'lxml', from_encoding='utf-8')
    for article_body in soup.find_all('div', itemprop="articleBody"):
        # scrap image
        imageTag = article_body.find('div', 'thinCenter')
        try:
            img_url = imageTag.select('img')[0].get('data-src')
        except:
            print("there is no img source")
            return False
        img_url = imageTag.select('img')[0].get('data-src')
        if (img_url == None):
            print("there is no img source")
            return False
        content = ''
        for pTag in article_body.find_all('p'):
            content = content + str(pTag.text) + "\n"
        content = content + '\n\n'
        abs_content = summarizer.summarize(content)
        if (abs_content == ""):
            print("empty hightlight")
            return False
        print("img_url type : " + str(type(img_url)))
        os.system("wget -O ./dm_data/thumbnail/thumbnail" + str(count) + ".jpg " + img_url)

        content = content + "@highlight\n\n" + abs_content
        open_output_file = open(os.path.join(output_dir, "content/content") + str(count) + ".txt", "w")
        open_output_file.write(content)
        open_output_file.close()
        return True

def save_data_from(url, count):
    print("starting save_data_from func")
    url = urlEncode(url)
    try:
        web_source = urllib.request.urlopen(url)
    except:
        print("bad url : not found...")
        return False
    soup = BeautifulSoup(web_source, 'lxml', from_encoding='utf-8')
    for article_body in soup.find_all('div', itemprop="articleBody"):
        # scrap image
        imageTag = article_body.find('div', 'artSplitter')
        try:
            img_url = imageTag.select('img')[0].get('data-src')
        except:
            print("there is no img source")
            return False
        img_url = imageTag.select('img')[0].get('data-src')
        if (img_url == None):
            print("there is no img source")
            return False
        # scrap content
        content = ''
        for pTag in article_body.find_all('p'):
            content = content + str(pTag.text) + "\n"
        # make abstract of content
        content = content + '\n\n'
        abs_content = summarizer.summarize(content)
        if (abs_content == ""):
            print("empty hightlight")
            return False
        
        print("img_url type : " + str(type(img_url)))
        os.system("wget -O ./dm_data/thumbnail/thumbnail" + str(count) + ".jpg " + img_url)
        
        content = content + "@highlight\n\n" + abs_content
        open_output_file = open(os.path.join(output_dir, "content/content") + str(count) + ".txt", "w")
        open_output_file.write(content)
        open_output_file.close()
        return True
        
        
def get_data(start_page_num, page_num):
    count = 0
    temp_url = 0
    for idx in range(start_page_num, page_num): # for each page
        current_search_page_url = URL_TARGET + str(10*idx) + URL_TYPE + str(10) + URL_REST
        web_source = urllib.request.urlopen(current_search_page_url)
        # soup = BeautifulSoup(response.read().decode('utf-8'))
        soup = BeautifulSoup(web_source.read().decode('utf-8'), 'lxml', from_encoding='utf-8')
        for title in soup.find_all('div', 'sch-result sport cleared'):
            print("count : %i" % count)
            print("url for count : %s" % temp_url)
            print("current url : %s" % current_search_page_url)
            print("current index : %i" % idx)
            title_link = title.select('a')
            article_URL = "https://www.dailymail.co.uk" + title_link[0]['href']
            print("article content page url : " + article_URL)
            # save content and thumbnail
            is_image_exist = True
            is_image_exist = save_data_from(article_URL, count)
            if not is_image_exist:
                is_image_exist = try_save_data_with_thinCenter_from(article_URL, count)
                print("\n\n\n checking the thinCenter div \n\n\n")
            
            if is_image_exist:
            # save headline
                temp_url = 10*idx
                headline_link = title.select('h3')
                headline = headline_link[0].select('a')[0].text
                open_output_file = open(os.path.join(output_dir, "headline/headline") + str(count) + ".txt", "w")
                open_output_file.write(headline)
                open_output_file.close()
                print("%i th data downloaded" % count)
                count = count + 1
            
            


def main():
    # crawl football news from Daily mail up to 22000 pages with 10 contents
    start_page_num = 0
    page_num = 22000

    # make directories for data to be stored
    content_dir = os.path.join(output_dir, "content/")
    headline_dir = os.path.join(output_dir, "headline/")
    thumbnail_dir = os.path.join(output_dir, "thumbnail/")
    make_dir(content_dir)
    make_dir(headline_dir)
    make_dir(thumbnail_dir)

    # crawl the data
    get_data(start_page_num, page_num)

if __name__ == '__main__': main()
