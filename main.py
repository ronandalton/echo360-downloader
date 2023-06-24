#!/usr/bin/env python3

""" A bulk downloader script for Echo360 lecture recordings. """

# Last updated 2023-06-24

import requests
import os
import sys
import re


HD_QUALITY = True
OUTPUT_DIRECTORY = "output"
COOKIES_FILE = "cookies.txt"

ECHO360_URL_NO_PREFIX = "echo360.net.au"
ECHO360_URL = f"https://{ECHO360_URL_NO_PREFIX}"
EXAMPLE_URL = f"{ECHO360_URL}/section/xxxxxx/home"
URL_REGEX = r"^" + re.escape(ECHO360_URL) + r"/section/([0-9a-f-]+)/home$"
VIDEO_FILE_TYPE = "mp4"


def get_section_id():
    while True:
        url = input("Enter URL: ").strip()

        match = re.search(URL_REGEX, url)

        if match is not None:
            return match.group(1)

        print("Error: Invalid URL format.")
        print(f"       Expected a URL that looks like {EXAMPLE_URL}")


def read_cookie_file(file_name, target_domain):
    cookies = dict()

    with open(file_name) as file:
        data = file.read().splitlines()

    if len(data) == 0:
        raise RuntimeError("Cookie file must not be empty")

    if data[0] not in ["# Netscape HTTP Cookie File", "# HTTP Cookie File"]:
        raise RuntimeError("Not a recognized cookie file")

    for line in data:
        if len(line) == 0 or line[0] == '#':
            continue

        items = line.split('\t')

        if len(items) != 7:
            raise RuntimeError("Invalid number of columns in cookies file")

        this_domain = items[0]

        if this_domain.startswith('.'):
            this_domain = this_domain[1:]

        if this_domain != target_domain:
            continue

        key = items[5]
        value = items[6]
        cookies[key] = value

    return cookies


def download_syllabus(section_id, cookies):
    url = f"{ECHO360_URL}/section/{section_id}/syllabus"
    response = requests.get(url, cookies=cookies)

    response.raise_for_status()

    if not response.headers['content-type'].startswith('application/json'):
        raise RuntimeError("Bad response (are your cookies up to date?)")

    try:
        return response.json()
    except Exception:
        raise RuntimeError("Could not parse response")


def extract_media_ids(syllabus_json):
    try:
        media_ids = []

        for entry in syllabus_json['data']:
            medias = entry['lesson']['medias']

            medias = list(filter(lambda media: media['mediaType'] == 'Video'
                                 and media['isAvailable'] is True, medias))

            if len(medias) == 0:
                continue

            media_ids.append(medias[0]['id'])

        return media_ids
    except Exception:
        raise RuntimeError("Some fields missing (please report this!)")


def get_download_links(media_ids, hd_version=True):
    download_links = []  # list of lists of links for each lesson

    base_url = f"{ECHO360_URL}/media/download"
    quality = "hd" if hd_version else "sd"
    file_type = VIDEO_FILE_TYPE

    for media_id in media_ids:
        lesson_video_links = []

        for num in [1, 2]:
            video_url = f"{base_url}/{media_id}/{quality}{num}.{file_type}"
            lesson_video_links.append(video_url)

        download_links.append(lesson_video_links)

    return download_links


def download_lessons(download_links, output_dir, cookies):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    for lesson_index, lesson_video_urls in enumerate(download_links):
        lesson_folder_name = f"Lecture {lesson_index + 1}"
        lesson_output_dir = os.path.join(output_dir, lesson_folder_name)

        print(f"Lecture {lesson_index + 1}:")
        download_videos(lesson_video_urls, lesson_output_dir, cookies)


def download_videos(video_urls, output_dir, cookies):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    for index, video_url in enumerate(video_urls):
        print(f"    Downloading video {index + 1}...")

        video_file_name = os.path.join(output_dir, f"vid_{index + 1}.mp4")

        response = requests.get(video_url, cookies=cookies, stream=True)
        response.raise_for_status()

        with open(video_file_name, 'wb') as handle:
            for block in response.iter_content(1024):
                handle.write(block)


def main():
    section_id = get_section_id()

    try:
        cookies = read_cookie_file(COOKIES_FILE, ECHO360_URL_NO_PREFIX)

        if len(cookies) == 0:
            sys.exit(f"Error: No cookies for {ECHO360_URL_NO_PREFIX} found")
    except Exception as e:
        sys.exit(f"Error reading cookies file: {e}")

    print("Getting download info...")

    try:
        syllabus_json = download_syllabus(section_id, cookies)
    except Exception as e:
        sys.exit(f"Error getting lectures info: {e}")

    try:
        media_ids = extract_media_ids(syllabus_json)
    except Exception as e:
        sys.exit(f"Error parsing download info: {e}")

    download_links = get_download_links(media_ids, HD_QUALITY)

    print(f"{len(download_links)} lecture recordings found.")

    try:
        download_lessons(download_links, OUTPUT_DIRECTORY, cookies)
    except Exception as e:
        sys.exit(f"Error while downloading videos: {e}")

    print("Download complete!")


if __name__ == '__main__':
    main()
