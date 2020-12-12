#!/usr/bin/python3

import os
import time
import logging
import requests
import config
from plexapi.myplex import MyPlexAccount


def init_logging():
    filename = os.path.splitext(os.path.abspath(__file__))[0]
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler('%s.log' % filename)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)


def get_slug(name):
    name = name.lower()

    for char in ["'", "\"", ",", ".", ":"]:
        name = name.replace(char, "")

    return name.replace(" ", "-")


if __name__ == "__main__":
    init_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting")

    account = MyPlexAccount(config.account_username, config.account_password)
    plex = account.resource(config.server_name).connect()
    logger.info("[+] Successfully connected to the server")

    movies = plex.library.section('Movies')

    duplicates = []
    duplicates_uncertain = []
    movies_without_imdb_tag = []

    for video in movies.search():
        title = video.title
        logger.debug("[.] %s " % title)

        url = "https://flixable.com/"

        temp_url = requests.compat.urljoin(url, "search.php")
        r = requests.get(temp_url, params={"query": title, "service": "netflix", "country": "ca"})
        if r.status_code != 200:
            logger.error("[!] initial HTTP request with code %s" % r.status_code)
            continue

        movs = r.json()

        found = False

        if movs:
            slug_from_plex = get_slug(title)
            for elem in movs:
                slug_from_query = elem['slug']
                if slug_from_query == slug_from_plex:
                    duplicates.append("{}\n{}\n".format(title, str(movs)))
                    found = True
                    continue

            if not found:
                duplicates_uncertain.append("{}\n{}\n".format(title, str(movs)))
        else:
            logger.warning("[-] (%s) No result on Flixable" % title)
        logger.info("")

    # Writing results to file
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "on-netflix-and-plex_%s.txt" % time.strftime("%Y%m%d-%H%M%S"))
    if duplicates:
        with open(filename, "w") as f:
            f.write("===== BOTH ON NETFLIX AND PLEX =====\n")
            for elem in duplicates:
                f.write("%s\n" % elem)

    if duplicates_uncertain:
        with open(filename, "a") as f:
            f.write("\n===== UNCERTAIN =====\n")
            for elem in duplicates_uncertain:
                f.write("%s\n" % elem)

    logger.info("Ending")
