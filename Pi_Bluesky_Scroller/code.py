# SPDX-FileCopyrightText: 2024 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
Bluesky_RPi_TFT_Scroller code.py
Infinitely scroll Bluesky posts on a 320x240 pixel TFT
"""
import json
import os
import sys

import requests
import webview

FEEDLINK_RETROCOMPUTING = (
    "https://bsky.app/profile/did:plc:tbo4hkau3p2itkar2vsnb3gp/feed/aaabo5oe7bzok"
)

# Un-comment a single key inside of FEED_ARGS and set it's value to the feed, list or search
# that you want to scroll.
FETCH_ARGS = {
    # "feed_share_link": FEEDLINK_RETROCOMPUTING,
    # "feed_share_link": "https://bsky.app/profile/did:plc:463touruejpokvutnn5ikxb5/lists/3lbfdtahfzt2a", # pylint: disable=line-too-long
    # "search_args": {"q": "Adafruit", "sort": "latest"}
    "search_args": {"q": "#circuitpython", "sort": "latest"}
}


def at_feed_uri_from_share_link(share_link):
    """
    Converts a share link into an AT URI for that resource.

    :param share_link: The share link to convert.
    :return str: The AT URI pointing at the resource.
    """
    at_feed_uri = share_link.replace("https://bsky.app/profile/", "at://")
    if "/feed/" in share_link:
        at_feed_uri = at_feed_uri.replace("/feed/", "/app.bsky.feed.generator/")
    if "/lists/" in share_link:
        at_feed_uri = at_feed_uri.replace("/lists/", "/app.bsky.graph.list/")
    return at_feed_uri


def fetch_data(feed_share_link=None, search_args=None):
    """
    Fetch posts from Bluesky API and write them into the local cached
    data files. After posts are written locally iterates over them
    and downloads the relevant photos from them.

    Must pass either feed_share_link or search_args.

    :param feed_share_link: The link copied from Bluesky front end to share the feed or list.
    :param search_args: A dictionary containing at minimum a ``q`` key with string value of
        the hashtag or term to search for. See bsky API docs for other supported keys.
    :return: None
    """
    # pylint: disable=too-many-statements,too-many-branches
    if feed_share_link is None and search_args is None:
        # If both inputs are None, just use retrocomputing feed.
        feed_share_link = FEEDLINK_RETROCOMPUTING

    # if a share link input was provided
    if feed_share_link is not None:
        FEED_AT = at_feed_uri_from_share_link(feed_share_link)
        # print(FEED_AT)

        # if it's a feed
        if "/app.bsky.feed.generator/" in FEED_AT:
            URL = (f"https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed?"
                   f"feed={FEED_AT}&limit=30")
            headers = {"Accept-Language": "en"}
            resp = requests.get(URL, headers=headers)

        # if it's a list
        elif "/app.bsky.graph.list/" in FEED_AT:
            URL = (f"https://public.api.bsky.app/xrpc/app.bsky.feed.getListFeed?"
                   f"list={FEED_AT}&limit=30")
            headers = {"Accept-Language": "en"}
            resp = requests.get(URL, headers=headers)

        # raise error if it's an unknown type
        else:
            raise ValueError(
                "Only 'app.bsky.feed.generator' and 'app.bsky.graph.list' URIs are supported."
            )

    # if a search input was provided
    if search_args is not None:
        URL = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
        headers = {"Accept-Language": "en"}
        resp = requests.get(URL, headers=headers, params=search_args)

    with open(".data/raw_data.json", "wb") as f:
        # write raw response to cache
        f.write(resp.content)

    # Process the post data into a smaller subset
    # containing just the bits we need for showing
    # on the TFT.
    resp_json = json.loads(resp.text)
    processed_posts = {"posts": []}
    fetched_posts = None
    if "feed" in resp_json.keys():
        fetched_posts = resp_json["feed"]
    elif "posts" in resp_json.keys():
        fetched_posts = resp_json["posts"]

    for post in fetched_posts:
        cur_post = {}
        if "post" in post.keys():
            post = post["post"]
        cur_post["author"] = post["author"]["handle"]
        cur_post["text"] = post["record"]["text"]

        # image handling
        if "embed" in post.keys():
            cid = post["cid"]
            if "images" in post["embed"].keys():
                cur_post["image_url"] = post["embed"]["images"][0]["thumb"]
            elif "thumbnail" in post["embed"].keys():
                cur_post["image_url"] = post["embed"]["thumbnail"]
            elif (
                "external" in post["embed"].keys()
                and "thumb" in post["embed"]["external"].keys()
            ):
                cur_post["image_url"] = post["embed"]["external"]["thumb"]

            # if we actually have an image to show
            if "image_url" in cur_post.keys():
                # check if we already downloaded this image
                if f"{cid}.jpg" not in os.listdir("static/imgs/"):
                    print(f"downloading: {cur_post['image_url']}")

                    # download image and write to file
                    img_resp = requests.get(cur_post["image_url"])
                    with open(f"static/imgs/{cid}.jpg", "wb") as f:
                        f.write(img_resp.content)

                cur_post["image_file"] = f"{cid}.jpg"
        processed_posts["posts"].append(cur_post)

    # save the processed data to a file
    with open(".data/processed_data.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(processed_posts))


def read_cached_data():
    """
    Load the cached processed data file and return
    the data from within it.

    :return: The posts data loaded from JSON
    """
    with open(".data/processed_data.json", "r") as f:
        return json.load(f)


class Api:
    """
    API object for interaction between python code here
    and JS code running inside the page.
    """

    # pylint: disable=no-self-use
    def get_posts(self):
        """
        Fetch new posts data from Bluesky API, cache and return it.
        :return: Processed data containing everything necessary to show
            posts on the TFT.
        """
        fetch_data(**FETCH_ARGS)
        return read_cached_data()

    def check_quit(self):
        """
        Allows the python code to correctly handle KeyboardInterrupt
        more quickly.

        :return: None
        """
        # pylint: disable=unnecessary-pass
        pass

    def quit(self):
        window.destroy()
        sys.exit(0)


# create a webview and load the index.html page
window = webview.create_window(
    "bsky posts", "static/index.html", js_api=Api(),
    #width=320, height=240,
    width=640, height=480,
    x=0, y=0, #frameless=True, fullscreen=True

)
webview.start()
# webview.start(debug=True)  # use this one to enable chromium dev tools to see console.log() output from the page.
