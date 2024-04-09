import requests
from bs4 import BeautifulSoup
import os
import sys
import time

def log_message(message, log_file, console_output=False):
    with open(log_file, "a") as log:
        log.write(f"{message}\n")
    if console_output:
        print(message)

def get_absolute_url(base, link):
    if not base.endswith('/'):
        base = f"{base}/"
    if link.startswith('/'):
        link = link[1:]
    return f"{base}{link}"

def is_directory(link):
    return link.endswith('/')

def is_valid_link(link):
    return not link.startswith('..') and not link.startswith('/')

def download_from_directory(session, directory_url, save_path, log_file="download.log", console_output=False, delay=1):
    response = session.get(directory_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and is_valid_link(href):
            absolute_url = get_absolute_url(directory_url, href)
            if is_directory(href):
                new_dir = os.path.join(save_path, href)
                if not os.path.exists(new_dir):
                    os.makedirs(new_dir)
                download_from_directory(session, absolute_url, new_dir, log_file, console_output, delay)
            else:
                download_file(session, absolute_url, save_path, delay, log_file=log_file, console_output=console_output)

def download_file(session, url, save_path, delay, log_file, console_output):
    filename = url.split('/')[-1]
    file_path = os.path.join(save_path, filename)
    with session.get(url, stream=True) as r:
        r.raise_for_status()
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    log_message(f"Downloaded {filename} to {save_path}", log_file, console_output)
    time.sleep(delay)  # Respectful delay to avoid hammering the server

def calculate_total_size(session, directory_url, log_file="size.log", console_output=False):
    """
    Calculate the total size of files in a directory and subdirectories at a given URL.
    Logs the calculated size to a specified log file and optionally prints to the console.
    """
    total_size = 0  # Initialize total size counter

    def navigate_and_sum(session, url):
        nonlocal total_size  # Access the outer total_size variable
        try:
            response = session.get(url)
            response.raise_for_status()  # Ensure we got a successful response
            soup = BeautifulSoup(response.content, 'html.parser')

            for link in soup.find_all('a'):
                href = link.get('href')
                if href and is_valid_link(href):
                    next_url = get_absolute_url(url, href)
                    if is_directory(href):
                        navigate_and_sum(session, next_url)  # Recurse into directory
                    else:
                        # This is a simplification, actual file size needs to be determined
                        # For real usage, you might need to make a HEAD request to get the Content-Length
                        # or use other methods depending on the server's response
                        log_message(f"Checking size for: {next_url}", log_file, console_output)
                        head = session.head(next_url)
                        size = head.headers.get('content-length', 0)
                        total_size += int(size)
        except Exception as e:
            log_message(f"Error navigating {url}: {e}", log_file, console_output)

    navigate_and_sum(session, directory_url)  # Start the recursive directory navigation

    # Once all sizes are summed, log and optionally print the total size
    readable_size = f"{total_size} bytes"
    log_message(f"Total size of all files: {readable_size}", log_file, console_output)

def count_files(session, directory_url, log_file="count.log", console_output=False):
    """
    Count files by extension in a directory and subdirectories at a given URL.
    Logs the count of each file type to a specified log file and optionally prints to the console.
    """
    file_counts = {}  # Dictionary to store file counts by extension

    def navigate_and_count(session, url):
        nonlocal file_counts  # Access the outer file_counts variable
        try:
            response = session.get(url)
            response.raise_for_status()  # Ensure we received a successful response
            soup = BeautifulSoup(response.content, 'html.parser')

            for link in soup.find_all('a'):
                href = link.get('href')
                if href and is_valid_link(href):
                    next_url = get_absolute_url(url, href)
                    if is_directory(href):
                        navigate_and_count(session, next_url)  # Recurse into directory
                    else:
                        # Extract the file extension and update the count
                        _, ext = os.path.splitext(href)
                        if ext:  # Ignore directories or files without an extension
                            ext = ext.lower()
                            file_counts[ext] = file_counts.get(ext, 0) + 1
        except Exception as e:
            log_message(f"Error navigating {url}: {e}", log_file, console_output)

    navigate_and_count(session, directory_url)  # Start the recursive directory navigation

    # Once all files are counted, log and optionally print the counts
    for ext, count in file_counts.items():
        message = f"Extension {ext}: {count} files"
        log_message(message, log_file, console_output)

def navigate_and_count_size(session, directory_url, log_file="navigate_count_size.log", console_output=False):
    """
    Navigate through a directory and its subdirectories to count files by extension and calculate total size.
    Logs the file count and total size for each file type to a specified log file and optionally prints to the console.
    """
    file_counts = {}
    file_sizes = {}

    def navigate_and_process(session, url):
        nonlocal file_counts, file_sizes
        try:
            response = session.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            for link in soup.find_all('a'):
                href = link.get('href')
                if href and is_valid_link(href):
                    next_url = get_absolute_url(url, href)
                    if is_directory(href):
                        navigate_and_process(session, next_url)
                    else:
                        _, ext = os.path.splitext(href)
                        ext = ext.lower() if ext else ".unknown"
                        file_counts[ext] = file_counts.get(ext, 0) + 1

                        # Assume file size is obtained from 'Content-Length'. Adjust as needed.
                        size = int(session.head(next_url).headers.get('Content-Length', 0))
                        file_sizes[ext] = file_sizes.get(ext, 0) + size

        except Exception as e:
            log_message(f"Error processing {url}: {e}", log_file, console_output)

    navigate_and_process(session, directory_url)

    # Logging the results
    for ext, count in file_counts.items():
        size = file_sizes.get(ext, 0)
        message = f"Extension {ext}: {count} files, Total size: {size} bytes"
        log_message(message, log_file, console_output)

def main():
    """Main function to run the script with a menu for user interaction."""
    print("Welcome to the Darkweb File Downloader")
    options = """
1. Download files from a directory
2. Calculate total size of files in a directory
3. Count files by extension in a directory
4. Count files and calculate total size
Select an option or 'q' to quit: """
    choice = input(options)
    url = input("Enter the directory URL: ")
    session = requests.session()
    console_output = input("Do you want to see verbose output in the console? (y/n): ").lower() == 'y'

    if choice == "1":
        save_path = input("Enter the save path for downloaded files: ")
        log_file = "download.log"
        download_from_directory(session, url, save_path, log_file=log_file, verbose=console_output)
    elif choice == "2":
        log_file = "calculate_size.log"
        calculate_total_size(session, url, log_file=log_file, verbose=console_output)
    elif choice == "3":
        log_file = "count_files.log"
        count_files(session, url, log_file=log_file, verbose=console_output)
    elif choice == "4":
        file_counts = {}
        file_sizes = {}
        log_file = "navigate_count_size.log"
        navigate_and_count_size(session, url, file_counts, file_sizes, log_file=log_file, verbose=console_output)
        log_message("File counts and sizes by extension:", log_file, console_output)
        for ext, count in file_counts.items():
            size = file_sizes.get(ext, 0)
            message = f"{ext}: {count} files, {size} bytes total"
            log_message(message, log_file, console_output)
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()
