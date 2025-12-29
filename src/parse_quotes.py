import csv
import os
import re
import requests
from bs4 import BeautifulSoup
from http import client

DAILY_STOIC_TXT_URL = "https://archive.org/stream/the-daily-stoic-366-meditations-on-wisdom-perseverance-and-the-art-of-living-pdfdrive.com/The-Daily-Stoic_-366-Meditations-on-Wisdom-Perseverance-and-the-Art-of-Living-PDFDrive.com-_djvu.txt"

# Fetch the website
response = requests.get(DAILY_STOIC_TXT_URL)
response.raise_for_status()

# Parse HTML and extract text from <pre> field
soup = BeautifulSoup(response.content, 'html.parser')
pre_element = soup.find('pre')

if pre_element:
    s = pre_element.get_text()
    
    # Parse by lines
    lines = s.splitlines()
    
    # Map to store date -> quote
    quotes_by_date = {}
    current_date = None
    current_quote = []
    
    # Pattern to match dates like "January 1st", "December 31st"
    date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)'
    
    for line in lines:
        if re.match(date_pattern, line.strip()):
            # Save previous quote if exists
            if current_date and current_quote:
                quotes_by_date[current_date] = '\n'.join(current_quote).strip()
            current_date = line.strip()
            current_quote = []
        elif current_date:
            # Stop at "STAYING STOIC" for December 31st
            if "STAYING STOIC" in line:
                if current_date:
                    quotes_by_date[current_date] = '\n'.join(current_quote).strip()
                break
            current_quote.append(line)
    
    # Save last quote
    if current_date and current_quote:
        quotes_by_date[current_date] = '\n'.join(current_quote).strip()
    
    # Clean up all quotes: remove extra whitespace
    for date in quotes_by_date:
        lines = quotes_by_date[date].split('\n')
        clean_lines = [line.strip() for line in lines if line.strip()]
        quotes_by_date[date] = '\n'.join(clean_lines)
    
    print(f"Total quotes captured: {len(quotes_by_date)}")

    # Save to CSV
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    csv_filepath = os.path.join(data_dir, 'quotes.csv')
    with open(csv_filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Date', 'Quote'])
        for date in sorted(quotes_by_date.keys()):
            writer.writerow([date, quotes_by_date[date]])
    
    print(f"Quotes saved to {csv_filepath}")
else:
    print("No <pre> element found")