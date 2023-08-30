#!/usr/bin/env python3

""" A bulk downloader script for Echo360 lecture recordings.
    The '-x' option enables the experimental downloader. Use this
    option if downloading is not enabled for your course.
    Note that yt-dlp and ffmpeg must be installed for this option to work. """

# Last updated 2023-08-29

import argparse
import requests
import os
import sys
import re
import subprocess
from urllib.parse import urlparse, unquote


DEFAULT_COOKIES_FILE = "cookies.txt"
DEFAULT_OUTPUT_DIR = "output"
YT_DLP_EXECUTABLE = "yt-dlp"
# the following 3 options only apply to the basic downloader
DOWNLOAD_SD_VIDEO_FILES = False
DOWNLOAD_HD_VIDEO_FILES = True
DOWNLOAD_AUDIO_FILES = False
CONCURRENT_DOWNLOAD_FRAGMENTS = 40  # only applies to experimental downloader

URL_REGEX = r"^(https://[^/]+)(/.*)$"
SECTION_PATH_URL_REGEX = r"^/section/([^/]+)/home"
LESSON_PATH_URL_REGEX = r"^/lesson/([^/]+)/classroom"
EXAMPLE_SECTION_URL = "https://echo360.net.au/section/xxxxxx/home"
EXAMPLE_LESSON_URL = "https://echo360.net.au/lesson/xxxxxx/classroom"
URL_HELPER_MESSAGE = "    Expected a URL that looks like one of the following:" \
        + f"\n    - {EXAMPLE_SECTION_URL}" \
        + f"\n    - {EXAMPLE_LESSON_URL}"
M3U8_URL_REGEX = r'\\"uri\\":\\"(https:\\/\\/.*?\\/s[0-2]_(?:a|v|av).m3u8)\?'


base_url = ""


def main():
    args = parse_args()

    try:
        validate_args(args)
    except Exception as e:
        sys.exit(f"Error: {e}")

    run_downloader(args.url, args.cookies_file_path, args.output_dir,
                   args.start_index, args.experimental_downloader)


def parse_args():
    parser = argparse.ArgumentParser(
            description="Download Echo360 lecture recordings.")

    parser.add_argument('url', nargs='?', metavar='URL', default=None,
                        help='Echo360 URL to download (leave blank to be prompted for this)')
    parser.add_argument('-x', '--experimental-mode',
                        dest='experimental_downloader', action='store_true',
                        help='enable experimental mode (default: off)')
    parser.add_argument('-c', '--cookies-file', metavar='FILE', dest='cookies_file_path',
                        default=DEFAULT_COOKIES_FILE,
                        help=f'path to cookies file to load cookies from (default: {DEFAULT_COOKIES_FILE})')
    parser.add_argument('-o', '--output-dir', metavar='PATH', dest='output_dir',
                        default=DEFAULT_OUTPUT_DIR,
                        help=f'directory to store downloaded lessons in (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--skip', metavar='NUMBER', dest='start_index', type=int, default=0,
                        help='number of lessons to skip when downloading multiple lessons')

    return parser.parse_args()


def validate_args(args):
    if (args.start_index < 0):
        raise RuntimeError("Number of lessons to skip must not be less than zero")


def run_downloader(url, cookies_file_path, output_dir, start_index=0,
                   experimental_downloader=False):
    global base_url

    if experimental_downloader:
        print("### Using experimental downloader ###")

        if not yt_dlp_is_installed():
            sys.exit("Error: yt-dlp executable not found (required by "
                     "experimental downloader)")

    if url is None:
        base_url, url_type, page_id = get_download_target_from_user()
    else:
        try:
            base_url, url_type, page_id = parse_url(url)
        except Exception as e:
            sys.exit(f"Error: {e}\n" + URL_HELPER_MESSAGE)

    try:
        cookies = read_cookies_file(cookies_file_path, base_url)
    except Exception as e:
        sys.exit(f"Error reading cookies file: {e}")

    if url_type == 'section':
        download_multiple_lessons(page_id, cookies, cookies_file_path,
                                  output_dir, start_index,
                                  experimental_downloader)
    elif url_type == 'lesson':
        download_single_lesson(page_id, cookies, cookies_file_path,
                               output_dir, experimental_downloader)


def yt_dlp_is_installed():
    try:
        subprocess.run([YT_DLP_EXECUTABLE, "--version"],
                       stdout=subprocess.DEVNULL, check=True)
    except Exception:
        return False

    return True


def get_download_target_from_user():
    while True:
        url = input("Enter URL: ").strip()

        try:
            return parse_url(url)
        except Exception:
            pass

        print("Error: Invalid URL format")
        print(URL_HELPER_MESSAGE)


def parse_url(url):
    match = re.search(URL_REGEX, url)

    if match is not None:
        base_url = match.group(1)
        path_url = match.group(2)

        path_match = re.search(SECTION_PATH_URL_REGEX, path_url)

        if path_match is not None:
            section_id = path_match.group(1)
            return base_url, 'section', section_id

        path_match = re.search(LESSON_PATH_URL_REGEX, path_url)

        if path_match is not None:
            lesson_id = path_match.group(1)
            return base_url, 'lesson', lesson_id

    raise ValueError("Invalid URL format")


def download_multiple_lessons(section_id, cookies, cookies_file_path,
                              output_dir, start_index,
                              experimental_downloader):
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
            download_lessons(lesson_ids, output_dir, cookies, start_index,
                             True, cookies_file_path)
        else:
            download_lessons(lesson_ids, output_dir, cookies, start_index)
    except Exception as e:
        sys.exit(f"Error while downloading lectures: {e}")

    print("Download complete!")


def download_single_lesson(lesson_id, cookies, cookies_file_path,
                           output_dir, experimental_downloader):
    print("Downloading lecture:")

    try:
        if experimental_downloader:
            download_lesson_experimental_version(lesson_id, output_dir,
                                                 cookies, cookies_file_path)
        else:
            download_lesson_basic_version(lesson_id, output_dir, cookies)
    except Exception as e:
        sys.exit(f"Error while downloading lecture: {e}")

    print("Download complete!")


def read_cookies_file(file_path, target_domain):
    target_domain_no_prefix = target_domain[len("https://"):]
    if target_domain_no_prefix.startswith("www."):
        target_domain_no_prefix = target_domain_no_prefix[len("www."):]

    cookies = dict()

    with open(file_path) as file:
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

        if this_domain != target_domain_no_prefix:
            continue

        key = items[5]
        value = items[6]
        cookies[key] = value

    if len(cookies) == 0:
        raise RuntimeError(f"No cookies for {target_domain_no_prefix} found")

    return cookies


def download_syllabus(section_id, cookies):
    url = f"{base_url}/section/{section_id}/syllabus"
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
            lesson_ids += extract_lesson_ids_recursive(entry)

        return lesson_ids
    except Exception:
        raise RuntimeError("Some fields missing (please report this!)")


def extract_lesson_ids_recursive(syllabus_entry):
    if syllabus_entry['type'] == 'SyllabusLessonType':
        if syllabus_entry['lesson']['hasContent'] is True and \
                syllabus_entry['lesson']['hasVideo'] is True:
            return [syllabus_entry['lesson']['lesson']['id']]
        else:
            return []
    elif syllabus_entry['type'] == 'SyllabusGroupType':
        lesson_ids = []

        for entry in syllabus_entry['lessons']:
            lesson_ids += extract_lesson_ids_recursive(entry)

        return lesson_ids
    else:
        return []


def download_lessons(lesson_ids, output_dir, cookies, start_index=0,
                     experimental_version=False, cookies_file_path=None):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    for lesson_index in range(start_index, len(lesson_ids)):
        lesson_id = lesson_ids[lesson_index]

        print(f"Lecture {lesson_index + 1}:")

        lesson_output_dir = os.path.join(output_dir,
                                         f"Lecture {lesson_index + 1}")

        if experimental_version:
            download_lesson_experimental_version(lesson_id, lesson_output_dir,
                                                 cookies, cookies_file_path)
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
    lesson_info = download_lesson_info(lesson_id, cookies)

    try:
        if lesson_info['data'][0]['hasContent'] is False or \
                lesson_info['data'][0]['hasVideo'] is False:
            return []

        media_urls = []

        media = lesson_info['data'][0]['video']['media']['media']['current']

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
    except RuntimeError as e:
        raise e
    except Exception:
        raise RuntimeError("Some fields missing while parsing lesson info "
                           "(please report this!)")


def download_lesson_info(lesson_id, cookies):
    url = f"{base_url}/lesson/{lesson_id}/media"
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
                                         cookies_file_path):
    print("    Downloading webpage...")
    lesson_video_urls = get_m3u8_download_links(lesson_id, cookies)

    download_m3u8_videos(lesson_video_urls, output_dir,
                         cookies_file_path)


def get_m3u8_download_links(lesson_id, cookies):
    page_url = f"{base_url}/lesson/{lesson_id}/classroom"

    response = requests.get(page_url, cookies=cookies)

    response.raise_for_status()

    urls_found = list(set(re.findall(M3U8_URL_REGEX, response.text)))
    urls_found = list(filter(lambda url: url.endswith("_av.m3u8"), urls_found))

    if len(urls_found) == 0:
        raise RuntimeError("No video URLs found")

    urls_found = list(map(lambda url: url.replace(r"\/", "/"), urls_found))

    urls_found.sort(key=lambda url: url.split('/')[-1])

    return urls_found


def download_m3u8_videos(video_urls, output_dir, cookies_file_path):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    for index, video_url in enumerate(video_urls):
        print(f"    Downloading video {index + 1}...")

        video_file_name = os.path.join(output_dir, f"hd{index + 1}.mp4")

        try:
            subprocess.run([YT_DLP_EXECUTABLE, "--cookies", cookies_file_path,
                            "--concurrent-fragments",
                            str(CONCURRENT_DOWNLOAD_FRAGMENTS), "--output",
                            video_file_name, video_url], check=True)
        except Exception:
            raise RuntimeError("External download command failed")


if __name__ == '__main__':
    main()
