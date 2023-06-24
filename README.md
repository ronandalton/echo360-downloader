# Echo360 Bulk Video Downloader

This script allows you to download all of your lecture recordings
from the Echo360 website (https://echo360.net.au), without having
to manually click on each download button separately.

## Limitations:

- Designed to work for New Zealand universities, may not work
in other countries.
- Downloading is only supported for courses that have the download
option enabled. If downloading is disabled (which is the default),
I recommend emailing your lecturer nicely and asking them to enable
downloading :)

## Usage:

1. Download the script and place it in a new directory somewhere.
Note that you will need Python installed in order to run the script.
2. Log into the Echo360 site using your web browser.
3. Use a browser extension to obtain a cookies.txt file.
Extensions are available for both
[Chrome](https://chrome.google.com/webstore/search/cookies.txt) and
[FireFox](https://addons.mozilla.org/en-US/firefox/search/?q=cookies.txt).
I recommend [this](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)
one for FireFox. Place this file in the same directory as the script.
4. Open a terminal in the directory with the script and cookies.txt file in
it. Run the script:
```python3 main.py```
5. Find the course you want to download the lectures for and copy the URL
for the page that lists all the lectures.
6. Paste the URL into the program and press enter.
7. Lectures will be downloaded into the "output" folder.

## Issues

If you find any issues with this script or the Echo360 website updates
and causes the script to break, create an issue on the issue tracker
and I'll do my best to resolve it.
