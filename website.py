import concurrent.futures
from dataclasses import dataclass, field
from typing import Dict, Set

import requests
from bs4 import BeautifulSoup
from dataclasses_json import dataclass_json

import exceptions
import url_utils
from counter import Counter
from logger import logger


@dataclass_json
@dataclass
class WebsiteStatus:
    links: Dict[str, int] = field(default_factory=dict)
    broken_links: Set[str] = field(default_factory=set)
    dup_images: Set[str] = field(default_factory=list)


class Link:
    def __init__(self, url, depth, is_broken=False, is_img=False):
        self.url = url
        self.depth = depth
        self.occurrences = Counter()
        self.is_broken = is_broken
        self.is_img = is_img

    def get_html(self) -> BeautifulSoup:
        try:
            response = requests.get(self.url)
        except requests.exceptions.RequestException:
            logger.exception("Could not handle request")
            raise

        if response.status_code == 200:
            return BeautifulSoup(response.text, features="html.parser")

        if response.status_code // 3 == 3:
            self.url = response.headers['Location']
            return self.get_html()

        if response.status_code == 404:
            raise exceptions.BrokenLink()

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, l):
        return self.url == l.url


class Website:
    def __init__(self, url: str):
        if not url_utils.is_valid_url(url):
            raise requests.exceptions.InvalidURL()

        self._host = url_utils.get_hostname(url)
        self.url = url

    # todo: minor refactor
    def get_links(self, max_workers=8):
        visited = set()
        links = set()
        depth = Counter()

        link = Link(self.url.lower(), depth)
        logger.info(f"Root url is {link.url}")

        links.add(link)
        visited.add(link)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            while links:
                depth += 1
                logger.info(f"Collecting depth {depth} links")

                future_links_html = {executor.submit(link.get_html): link for link in links}
                links.clear()

                for future_link_html in concurrent.futures.as_completed(future_links_html):
                    try:
                        link_html = future_link_html.result()

                        logger.info(f"Trying to collect links from {future_links_html[future_link_html].url}")
                        a_elems = link_html.find_all('a')
                        for a_elem in a_elems:
                            link_url = self._make_link_url(a_elem, 'href')
                            if link_url:
                                new_link = Link(link_url, depth)

                                if new_link not in visited:
                                    links.add(new_link)
                                    visited.add(new_link)
                                else:
                                    link.occurrences += 1
                        logger.info(f"Successfully collected links")

                    except exceptions.BrokenLink:
                        logger.warn(f"{future_links_html[future_link_html].url} is broken")
                        future_links_html[future_link_html].is_broken = True
                    except requests.RequestException:
                        logger.exception(
                            f"Something went wrong while requesting {future_links_html[future_link_html].url}")
                    except Exception:
                        logger.exception("Unknow error occurred")

                logger.info(f"Visited {len(visited)} and has {len(links)} more links to go")

        return visited

    def _make_link_url(self, elem, attr):
        path = elem.get(attr)
        if path:
            path = path.lower()
            link_url = path if path[-1] != '/' else path[:-1]
            if path[0] == '/':
                link_url = self._host + path

            if url_utils.get_hostname(link_url) == self._host:
                return link_url
        return None

    def get_status(self):
        website_status = WebsiteStatus()
        for link in self.get_links():
            if link.url not in website_status.links:
                website_status.links[link.url] = link.depth.value
            if link.is_broken:
                website_status.broken_links.add(link.url)
            if link.is_img and link.occurrences > 1:
                website_status.dup_images.add(link.url)

        return website_status
