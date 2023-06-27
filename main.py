#!/usr/bin/env python3

""" A bulk downloader script for Echo360 lecture recordings.
    The '-x' option enables the experimental downloader. Use this
    option if downloading is not enabled for your course.
    Note that yt-dlp and ffmpeg must be installed for this option to work. """

# Last updated 2023-06-27

import requests
import os
import sys
import re
import subprocess
from urllib.parse import urlparse, unquote


OUTPUT_DIRECTORY = "output"
COOKIES_FILE = "cookies.txt"
YT_DLP_EXECUTABLE = "yt-dlp"
# the following 3 options only apply to the basic downloader
DOWNLOAD_SD_VIDEO_FILES = False
DOWNLOAD_HD_VIDEO_FILES = True
DOWNLOAD_AUDIO_FILES = False
CONCURRENT_DOWNLOAD_FRAGMENTS = 40  # only applies to experimental downloader

ECHO360_URL_NO_PREFIX = "echo360.net.au"
ECHO360_URL = f"https://{ECHO360_URL_NO_PREFIX}"
EXAMPLE_URL = f"{ECHO360_URL}/section/xxxxxx/home"
URL_REGEX = r"^" + re.escape(ECHO360_URL) + r"/section/([0-9a-f-]+)/home$"
VIDEO_FILE_TYPE = "mp4"
M3U8_URL_REGEX = r'\\"uri\\":\\"(https:\\/\\/.*?\\/s[0-2]_(?:a|v|av).m3u8)\?'


def main():
    args = sys.argv[1:]

    if "-x" in args:
        run_downloader(True)
    else:
        run_downloader(False)


def run_downloader(experimental_downloader=False):
    if experimental_downloader:
        print("### Using experimental downloader ###")

    try:
        cookies = read_cookies_file(COOKIES_FILE, ECHO360_URL_NO_PREFIX)

        if len(cookies) == 0:
            sys.exit(f"Error: No cookies for {ECHO360_URL_NO_PREFIX} found")
    except Exception as e:
        sys.exit(f"Error reading cookies file: {e}")

    section_id = get_section_id()

    print("Getting download info...")

    try:
        syllabus_json = download_syllabus(section_id, cookies)
    except Exception as e:
        sys.exit(f"Error getting lectures info: {e}")

    try:
        lesson_ids = extract_lesson_ids(syllabus_json)
    except Exception as e:
        sys.exit(f"Error parsing download info: {e}")

    print(f"{len(lesson_ids)} lecture recordings found.")

    try:
        if experimental_downloader:
            download_lessons(lesson_ids, OUTPUT_DIRECTORY, cookies, True,
                             COOKIES_FILE)
        else:
            download_lessons(lesson_ids, OUTPUT_DIRECTORY, cookies)
    except Exception as e:
        sys.exit(f"Error while downloading videos: {e}")

    print("Download complete!")


def get_section_id():
    while True:
        url = input("Enter URL: ").strip()

        match = re.search(URL_REGEX, url)

        if match is not None:
            return match.group(1)

        print("Error: Invalid URL format.")
        print(f"       Expected a URL that looks like {EXAMPLE_URL}")


def read_cookies_file(file_name, target_domain):
    cookies = dict()

    with open(file_name) as file:
        data = file.read().splitlines()

    if len(data) == 0:
        raise RuntimeError("Cookie file must not be empty")

    if data[0] not in ["# Netscape HTTP Cookie File", "# HTTP Cookie File"]:
        raise RuntimeError("Not a recognized cookie file")

    for i, line in enumerate(data):
        if line.startswith("#HttpOnly_"):
            data[i] = line[10:]

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


def extract_lesson_ids(syllabus_json):
    try:
        lesson_ids = []

        for entry in syllabus_json['data']:
            if entry['lesson']['hasContent'] is True and \
                    entry['lesson']['hasVideo'] is True:
                lesson_ids.append(entry['lesson']['lesson']['id'])

        return lesson_ids
    except Exception:
        raise RuntimeError("Some fields missing (please report this!)")


def download_lessons(lesson_ids, output_dir, cookies,
                     experimental_version=False, cookies_file=None):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    for lesson_index, lesson_id in enumerate(lesson_ids):
        print(f"Lecture {lesson_index + 1}:")

        lesson_output_dir = os.path.join(output_dir,
                                         f"Lecture {lesson_index + 1}")

        if experimental_version:
            download_lesson_experimental_version(lesson_id, lesson_output_dir,
                                                 cookies, cookies_file)
        else:
            download_lesson_basic_version(lesson_id, lesson_output_dir,
                                          cookies)


def download_lesson_basic_version(lesson_id, output_dir, cookies):
    print("    Downloading lecture info...")
    lesson_media_urls = get_media_download_links(lesson_id, cookies)

    if len(lesson_media_urls) == 0:
        raise RuntimeError("No downloadable content found for lecture")

    download_medias(lesson_media_urls, output_dir, cookies)


def get_media_download_links(lesson_id, cookies):
    data = download_lesson_info(lesson_id, cookies)

    media_urls = []

    media = data['data'][0]['video']['media']['media']['current']

    for key in ["primaryFiles", "secondaryFiles", "tertiaryFiles",
                "quaternaryFiles"]:
        versions = media[key]

        if len(versions) == 0:
            continue

        if len(versions) != 2:
            raise RuntimeError(
                    "Unexpected number of video quality types found")

        if versions[0]['width'] > versions[1]['width']:
            versions = versions[::-1]

        if DOWNLOAD_SD_VIDEO_FILES:
            media_urls.append(versions[0]['s3Url'])

        if DOWNLOAD_HD_VIDEO_FILES:
            media_urls.append(versions[1]['s3Url'])

    if DOWNLOAD_AUDIO_FILES:
        for file_info in media["audioFiles"]:
            media_urls.append(file_info['s3Url'])

    return media_urls


def download_lesson_info(lesson_id, cookies):
    url = f"{ECHO360_URL}/lesson/{lesson_id}/media"
    response = requests.get(url, cookies=cookies)

    response.raise_for_status()

    if not response.headers['content-type'].startswith('application/json'):
        raise RuntimeError("Bad response (are your cookies up to date?)")

    try:
        return response.json()
    except Exception:
        raise RuntimeError("Could not parse response")


def download_medias(media_urls, output_dir, cookies):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    for index, media_url in enumerate(media_urls):
        print(f"    Downloading media file {index + 1}...")

        file_name = unquote(urlparse(media_url).path).split("/")[-1]

        response = requests.get(media_url, cookies=cookies, stream=True)
        response.raise_for_status()

        with open(os.path.join(output_dir, file_name), 'wb') as handle:
            for block in response.iter_content(1024):
                handle.write(block)


def download_lesson_experimental_version(lesson_id, output_dir, cookies,
                                         cookies_file):
    print("    Downloading webpage...")
    lesson_video_urls = get_m3u8_download_links(lesson_id, cookies)

    download_m3u8_videos(lesson_video_urls, output_dir,
                         cookies_file)


def get_m3u8_download_links(lesson_id, cookies):
    page_url = f"{ECHO360_URL}/lesson/{lesson_id}/classroom"

    response = requests.get(page_url, cookies=cookies)

    response.raise_for_status()

    urls_found = list(set(re.findall(M3U8_URL_REGEX, response.text)))
    urls_found = list(filter(lambda url: url.endswith("s1_av.m3u8") or
                      url.endswith("s2_av.m3u8"), urls_found))

    if len(urls_found) == 0:
        raise RuntimeError("No video URLs found")
    elif len(urls_found) != 2:
        raise RuntimeError("Unexpected number of video URLs found")

    urls_found = list(map(lambda url: url.replace(r"\/", "/"), urls_found))

    if urls_found[0].endswith("s2_av.m3u8"):
        urls_found = urls_found[::-1]

    return urls_found


def download_m3u8_videos(video_urls, output_dir, cookies_file):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    for index, video_url in enumerate(video_urls):
        print(f"    Downloading video {index + 1}...")

        video_file_name = os.path.join(output_dir, f"hd{index + 1}.mp4")

        subprocess.run([YT_DLP_EXECUTABLE, "--cookies", cookies_file,
                        "--concurrent-fragments",
                        str(CONCURRENT_DOWNLOAD_FRAGMENTS), "--output",
                        video_file_name, video_url])


if __name__ == '__main__':
    main()
