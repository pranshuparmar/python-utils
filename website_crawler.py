import requests
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from urllib.parse import urlparse, urlunparse, urljoin


def clean_url(url):
    # Remove query parameters
    url_parts = list(urlparse(url))
    url_parts[4] = ''
    clean_url = urlunparse(url_parts)

    # Remove trailing '/'
    if clean_url.endswith('/'):
        clean_url = clean_url.rstrip('/')

    return clean_url


def is_website_url(url):
    parsed_url = urlparse(url)
    path = parsed_url.path
    if '.' not in path.split('/')[-1]:
        return True
    if path.endswith(('.html', '.htm', '.php', '.asp', '.aspx', '.jsp')):
        return True
    return False


# Function to get links associated with a domain (recursively)
def get_domain_links_recursive(url, domains, allowed_urls, disallowed_urls, headers, visited=None):
    if visited is None:
        visited = set()

    # Send a GET request to the URL
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("Error status code, skipping url: ", response.status_code, url)
            return visited
    except requests.exceptions.TooManyRedirects:
        print("Too many redirects error, skipping url: ", url)
        return visited
    except requests.exceptions.RequestException:
        print("An error occurred, skipping url: ", url)
        return visited

    # Parse the HTML content using BeautifulSoup
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.filterwarnings('always', category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(response.content, 'html.parser')
        if caught_warnings:
            print("An error occurred, skipping url: ", url)
            return visited

    # Get all the <a> tags from the HTML
    links = soup.find_all('a')

    # Iterate over each link
    for link in links:
        # Get the href attribute of the link
        href = link.get('href')

        if href:
            # Join the URL with the href attribute to get the absolute URL
            absolute_url = urljoin(url, href)

            # Parse the absolute URL
            parsed_url = urlparse(absolute_url)

            # Check if the netloc (domain) matches the desired domain
            if parsed_url.netloc in domains:
                # Check if the URL is explicitly allowed in robots.txt
                if any(allowed_url in absolute_url for allowed_url in allowed_urls):
                    pass
                # Check if the URL is present in disallowed URLs from robots.txt
                elif any(disallowed_url in absolute_url for disallowed_url in disallowed_urls):
                    print("Disallowed URL found, skipping url: ", absolute_url)
                    continue

                # Check if the URL ends with any word starting with '#'
                if not any(absolute_url.endswith(f'#{word}') for word in parsed_url.fragment.split()):
                    # Clean the absolute URL before checking
                    absolute_url = clean_url(absolute_url)

                    # Check if the absolute URL has been visited already
                    if absolute_url not in visited:
                        visited.add(absolute_url)
                        print(absolute_url)

                        if is_website_url(absolute_url):
                            # Recursively call the function on the absolute URL
                            get_domain_links_recursive(absolute_url, domains, allowed_urls, disallowed_urls, headers, visited)
    return visited


def is_url_allowed(url, headers, allowed_paths, disallowed_paths):
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

    try:
        response = requests.get(robots_url, headers=headers)
        response.raise_for_status()
        robots_content = response.text

        for line in robots_content.split('\n'):
            if line.strip() == 'Disallow:' or line.strip() == 'Allow:':
                continue
            elif line.startswith('Disallow:'):
                disallowed_path = line.split(':')[1].strip()
                disallowed_paths.append(disallowed_path)
            elif line.startswith('Allow:'):
                allowed_path = line.split(':')[1].strip()
                allowed_paths.append(allowed_path)

        for disallowed_path in disallowed_paths:
            if disallowed_path == '/':
                return False, [], []
            elif parsed_url.path.startswith(disallowed_path) and not any(parsed_url.path.startswith(path) for path in allowed_paths):
                return False, [], []

        return True, allowed_paths, disallowed_paths

    except requests.exceptions.RequestException:
        return True, [], []  # Allow access if there is an error retrieving robots.txt


def scrape_website(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    allowed_paths = []
    disallowed_paths = []
    is_allowed, allowed_paths, disallowed_paths = is_url_allowed(url, headers, allowed_paths, disallowed_paths)
    if is_allowed:
        domains = []
        parsed_url = urlparse(url)
        domains.append(parsed_url.netloc)
        if parsed_url.netloc.count('.') == 1:
            domains.append('www.' + parsed_url.netloc)

        # Call the function to get the domain links recursively
        links = get_domain_links_recursive(url, domains, allowed_paths, disallowed_paths, headers)

        # Print the list of links
        print("Final list: ")
        for link in links:
            print(link)
    else:
        print(f"Access to {url} is not allowed by robots.txt")


if __name__ == '__main__':
    # The URL to scrape
    url = 'https://hubengage.com'
    scrape_website(url)
