import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

# Function to get HTML content from a URL
def get_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print('Error fetching the URL:', e)
        return None

# Function to count keyword occurrences
# def count_keyword(html, keyword):
#     keyword = keyword.lower()
#     text = BeautifulSoup(html, 'html.parser').get_text().lower()
#     return text.count(keyword)

# Function to find all external links
def find_external_links(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    links = soup.find_all('a', href=True)
    external_links = []
    parsed_base_url = urlparse(base_url)
    base_domain = parsed_base_url.netloc

    for link in links:
        href = link.get('href')
        parsed_href = urlparse(href)

        # If the link is external (different domain)
        if parsed_href.netloc and parsed_href.netloc != base_domain:
            external_links.append(href)

    return external_links

# Main function
def main():
    # keyword = input("Enter the keyword: ")
    url = input("Enter the URL: ")

    html = get_html(url)
    if html is None:
        print('Failed to retrieve HTML content.')
        return

    # keyword_count = count_keyword(html, keyword)
    external_links = find_external_links(html, url)

    # print(f"\nKeyword '{keyword}' found {keyword_count} times in the page.")
    print("\nExternal Links:")
    for link in external_links:
        print(link)

if __name__ == "__main__":
    main()
