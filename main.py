#!/usr/bin/python3

import re
import os
import time
import json
import logging
import requests
import config
from plexapi.myplex import MyPlexAccount


def extract_imdb_id(text):
    search = re.search("imdb:\/\/([A-Za-z0-9]+)", text)
    return search.group(1)


def init_logging():
    filename = os.path.splitext(os.path.abspath(__file__))[0]
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler('%s.log' % filename)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)


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
        if "imdb://" not in video.guid:
            movies_without_imdb_tag.append(title)
            logger.warning("[-] No IMDB id for %s" % title)

        else:
            imdb_id_plex = extract_imdb_id(video.guid)
            logger.debug(imdb_id_plex)
            url = "https://ca.flixable.com/"

            temp_url = requests.compat.urljoin(url, "search.php")
            r = requests.get(temp_url, params={"query": title, "country": "ca"})
            if r.status_code != 200:
                logger.error("[!] initial HTTP request with code %s" % r.status_code)
                continue

            movs = json.loads(r.text)

            if movs:
                on_netflix = False
                no_imdb_link = False
                for mov in movs:
                    logger.debug(mov['id'])
                    full_url = requests.compat.urljoin(url, "title/%s" % mov['id'])
                    r2 = requests.get(full_url)
                    if r2.status_code != 200:
                        logger.error("[!] second HTTP request with code %s" % r2.status_code)
                        continue

                    text2 = r2.text
                    groups_found = re.search("imdb\.com\/title\/([A-Za-z0-9]+)", text2)
                    if not groups_found:
                        no_imdb_link = True
                    else:
                        for group in groups_found.groups():
                            if imdb_id_plex in group:
                                logger.warning("[+] %s is on Netflix! '%s' found in %s" % (title, imdb_id_plex, full_url))
                                duplicates.append(title)
                                on_netflix = True
                                break

                if not on_netflix and no_imdb_link:
                    logger.warning("[-] (%s) Results found, but without IDMB id so cannot compare (%s)" % (title, r.text))
                    duplicates_uncertain.append(title)
                elif not on_netflix:
                    logger.warning("[-] (%s) Results returned, but movie is not in the results (%s)" % (title, r.text))


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

    if movies_without_imdb_tag:
        with open(filename, "a") as f:
            f.write("\n===== UNKNOWN (NO IMDB TAG FOUND) =====\n")
            for elem in movies_without_imdb_tag:
                f.write("%s\n" % elem)

    logger.info("Ending")
