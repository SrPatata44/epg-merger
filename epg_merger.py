import requests
from lxml import etree
from datetime import datetime, timedelta

# CONFIGURATION
dynamic_epg_url = 'http://m3u4u.com/xml/x79znkxmpc4318qygk24'
radio_epg_file = 'radioguide.xml'
output_file = 'guia-izzi.xml'
repeat_days = 1  # Number of days to repeat radio schedule

# Fetch dynamic EPG from URL
response = requests.get(dynamic_epg_url)
response.raise_for_status()
dynamic_epg = etree.fromstring(response.content)

# Load and clean static radio EPG
with open(radio_epg_file, 'rb') as f:
    content = f.read().lstrip()
    radio_epg = etree.fromstring(content)

# Add <channel> entries from radio to dynamic EPG, avoiding duplicates
existing_channel_ids = {el.get('id') for el in dynamic_epg.findall('./channel')}
for channel in radio_epg.findall('./channel'):
    chan_id = channel.get('id')
    if chan_id not in existing_channel_ids:
        dynamic_epg.append(channel)
        existing_channel_ids.add(chan_id)

# Prepare today's midnight for offsetting programme times
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# Collect all channels seen in <programme>
programme_channel_ids = set()

# Repeat radio <programme> entries for N days with 90-minute durations
for programme in radio_epg.findall('./programme'):
    start_str = programme.get('start')
    channel = programme.get('channel')
    programme_channel_ids.add(channel)

    # Parse start time and timezone offset
    start_time = datetime.strptime(start_str[:14], "%Y%m%d%H%M%S").time()
    offset = start_str[14:]  # Keep the timezone offset

    for day in range(repeat_days):
        base_date = today + timedelta(days=day)
        start_dt = datetime.combine(base_date, start_time)
        stop_dt = start_dt + timedelta(minutes=90)

        # Fix edge case where stop wraps to the next day
        if stop_dt <= start_dt:
            stop_dt += timedelta(days=1)

        # Create new programme
        new_prog = etree.Element('programme')
        new_prog.set('start', start_dt.strftime("%Y%m%d%H%M%S") + offset)
        new_prog.set('stop', stop_dt.strftime("%Y%m%d%H%M%S") + offset)
        new_prog.set('channel', channel)

        # Copy children like <title>, <desc>, etc.
        for child in programme:
            new_prog.append(child)

        dynamic_epg.append(new_prog)

# Auto-generate <channel> elements if missing from both EPGs
for chan_id in programme_channel_ids - existing_channel_ids:
    channel_el = etree.Element('channel', id=chan_id)
    display_name = etree.Element('display-name', lang='es')
    display_name.text = chan_id  # fallback name
    channel_el.append(display_name)
    dynamic_epg.append(channel_el)

# Write merged EPG to file
tree = etree.ElementTree(dynamic_epg)
tree.write(output_file, encoding='utf-8', xml_declaration=True, pretty_print=True)

print(f"✅ Merged EPG saved to '{output_file}' with {repeat_days} days of 90-minute radio programming.")