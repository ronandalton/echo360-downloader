# Echo360 Bulk Video Downloader

This script allows you to download all of your lecture recordings
from the Echo360 website (https://echo360.net.au), without having
to manually click on each download button separately.

## Limitations

- Designed to work for New Zealand universities, may or may not work
in other countries.
- Downloading is only supported for courses that have the download
option enabled. There is an experimental mode that you can use to
attempt to bypass this restriction (see below for details), however
I would recommend just emailing your lecturer nicely and asking them
to enable downloads :)

## Usage

1. Download the script (main.py) and place it in a new directory somewhere.
Note that you will need Python installed in order to run the script.
2. Log into the Echo360 site using your web browser.
3. Use a browser extension to obtain a cookies.txt file.
Extensions are available for both
[Chrome](https://chrome.google.com/webstore/search/cookies.txt) and
[Firefox](https://addons.mozilla.org/en-US/firefox/search/?q=cookies.txt).
I recommend [this](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)
one for Firefox. Place this file in the same directory as the script.
4. Open a terminal in the directory with the script and cookies.txt file in
it. Run the script with `python3 main.py`.
5. Find the course you want to download the lectures for and copy the URL
for the page that lists all the lectures.
6. Paste the URL into the program and press enter.
7. Lectures will be downloaded into the "output" folder.

## Experimental Mode

There is a new experimental mode that attempts to download lectures,
even if the download option hasn't been enabled (no download button
in the user interface). To enable this mode you must pass the '-x'
command line option to the script when you run it, eg. `python3 main.py -x`.
Note that you will need to have [yt-dlp](https://github.com/yt-dlp/yt-dlp)
and [ffmpeg](https://ffmpeg.org/) installed for this to work. If you get
403 errors, it is probably an issue with your cookies file. Try clicking
into a video first and then creating a cookies.txt file, or logging out
and back in.

## Config

There are no command line configuration options at the moment, but
there are some constants at the top of the script that can be set.

## Issues

If you find any issues with this script or the Echo360 website updates
and causes the script to break, create an issue on the issue tracker
and I'll do my best to resolve it.
