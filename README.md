# Echo360 Bulk Video Downloader

This script allows you to download all of your lecture recordings from the
[Echo360](https://echo360.com/) website, without having to manually click on
each download button separately.

## Limitations

- Designed to work for New Zealand universities. It should work for educational
  institutions in other countries, but I haven't been able to test it.
- Downloading is only supported for courses that have the download option
  enabled. There is an experimental mode that you can use to attempt to bypass
  this restriction (see below for details), however I would recommend just
  emailing your lecturer nicely and asking them to enable downloads :)

## Getting Started

1. Download the script (main.py) and place it in a new directory somewhere.
Note that you will need Python installed in order to run the script.
2. Log into the Echo360 site using your web browser.
3. Use a browser extension to obtain a cookies.txt file. Extensions are
available for both
[Chrome](https://chrome.google.com/webstore/search/cookies.txt) and
[Firefox](https://addons.mozilla.org/en-US/firefox/search/?q=cookies.txt). I
recommend [this](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)
one for Firefox. Place this file in the same directory as the script.
4. Open a terminal in the directory with the script and cookies.txt file in it.
Run the script with `python3 main.py`.
5. Find the course you want to download the lectures for and copy the URL for
the page that lists all the lectures. You can also download a single lecture by
copying the URL while on the video page for that lecture.
6. Paste the URL into the program and press enter.
7. Lectures will be downloaded into the "output" folder.

## Usage

`python3 main.py [URL] [OPTIONS]...`

Note that if a URL is not provided as a command line argument, the user will be
prompted to enter one interactively.

## Options

The following command line arguments are supported:

| Option                            | Description                                                      |
|-----------------------------------|------------------------------------------------------------------|
| `-h` / `--help`                   | show a help message and exit                                     |
| `-x` / `--experimental-mode`      | enable experimental mode (default: off)                          |
| `-c FILE` / `--cookies-file FILE` | path to cookies file to load cookies from (default: cookies.txt) |
| `-o PATH` / `--output-dir PATH`   | directory to store downloaded lessons in (default: output)       |
| `--skip NUMBER`                   | number of lessons to skip when downloading multiple lessons      |

## Experimental Mode

There is a new experimental mode that attempts to download lectures, even if
the download option hasn't been enabled (no download button in the user
interface). To enable this mode you must pass the '-x' command line option to
the script when you run it, eg. `python3 main.py -x`. Note that you will need
to have [yt-dlp](https://github.com/yt-dlp/yt-dlp) and
[ffmpeg](https://ffmpeg.org/) installed for this to work. If you get 403
errors, it is probably an issue with your cookies file. Try clicking into a
video first and then creating a cookies.txt file, or logging out and back in.

## Issues

If you find any issues with this script or the Echo360 website updates and
causes the script to break, create an issue on the issue tracker and I'll do my
best to resolve it.
