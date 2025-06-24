import requests
from lxml import etree
from datetime import datetime, timedelta

# CONFIGURATION
dynamic_epg_url = 'http://m3u4u.com/xml/x79znkxmpc4318qygk24'
radio_epg_file = 'radioguide.xml'
output_file = 'guia-izzi.xml'
repeat_days = 1  # How many days to repeat radio schedule

# Fetch dynamic EPG from URL
response = requests.get(dynamic_epg_url)
response.raise_for_status()
dynamic_epg = etree.fromstring(response.content)

# Load and clean the static radio EPG
with open(radio_epg_file, 'rb') as f:
    content = f.read().lstrip()
    radio_epg = etree.fromstring(content)

# Add <channel> entries from radio to dynamic EPG
for element in radio_epg.findall('./channel'):
    dynamic_epg.append(element)

# Prepare today’s date at midnight for shifting programme times
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# Parse and repeat <programme> entries for N days with 90-minute durations
for programme in radio_epg.findall('./programme'):
    start_str = programme.get('start')
    channel = programme.get('channel')

    # Parse time portion from start string
    start_time = datetime.strptime(start_str[:14], "%Y%m%d%H%M%S").time()
    offset = start_str[14:]  # timezone offset like +0000 or -0500

    for day in range(repeat_days):
        base_date = today + timedelta(days=day)
        start_dt = datetime.combine(base_date, start_time)

        # Set stop time 90 minutes after start
        stop_dt = start_dt + timedelta(minutes=90)

        # Handle midnight crossing: if stop <= start, add 1 day
        if stop_dt <= start_dt:
            stop_dt += timedelta(days=1)

        # Create new <programme> element
        new_prog = etree.Element('programme')
        new_prog.set('start', start_dt.strftime("%Y%m%d%H%M%S") + offset)
        new_prog.set('stop', stop_dt.strftime("%Y%m%d%H%M%S") + offset)
        new_prog.set('channel', channel)

        # Copy children elements like <title>, <desc> etc.
        for child in programme:
            new_prog.append(child)

        # Append to dynamic EPG
        dynamic_epg.append(new_prog)

# Save merged EPG to output file
tree = etree.ElementTree(dynamic_epg)
tree.write(output_file, encoding='utf-8', xml_declaration=True, pretty_print=True)

print(f"✅ Merged EPG saved to '{output_file}' with {repeat_days} days of radio programming, each 90 minutes long.")