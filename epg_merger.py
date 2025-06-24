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

# Add <channel> entries from radio
for element in radio_epg.findall('./channel'):
    dynamic_epg.append(element)

# Parse and repeat <programme> entries for N days
for programme in radio_epg.findall('./programme'):
    start_str = programme.get('start')
    stop_str = programme.get('stop')
    channel = programme.get('channel')

    # Parse base datetime
    start_dt = datetime.strptime(start_str[:14], "%Y%m%d%H%M%S")
    stop_dt = datetime.strptime(stop_str[:14], "%Y%m%d%H%M%S")
    offset = start_str[14:]  # Preserve timezone offset

    for day in range(repeat_days):
        delta = timedelta(days=day)
        new_prog = etree.Element('programme')
        new_prog.set('start', (start_dt + delta).strftime("%Y%m%d%H%M%S") + offset)
        new_prog.set('stop', (stop_dt + delta).strftime("%Y%m%d%H%M%S") + offset)
        new_prog.set('channel', channel)

        # Copy children (<title>, <desc>, etc.)
        for child in programme:
            new_prog.append(child)

        dynamic_epg.append(new_prog)

# Save merged EPG
tree = etree.ElementTree(dynamic_epg)
tree.write(output_file, encoding='utf-8', xml_declaration=True, pretty_print=True)
print(f"✅ Merged EPG saved to '{output_file}' with {repeat_days} days of radio programming.")
