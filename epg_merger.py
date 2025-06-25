import requests
import copy
from lxml import etree
from datetime import datetime, timedelta

# CONFIGURATION
dynamic_epg_url = 'http://m3u4u.com/xml/x79znkxmpc4318qygk24'
radio_epg_file = 'radioguide.xml'
output_file = 'guia-izzi.xml'
repeat_days = 1  # Number of days to repeat radio schedule
block_minutes = 90  # Duration of each repeated block

# Fetch dynamic EPG from URL
response = requests.get(dynamic_epg_url)
response.raise_for_status()
dynamic_epg = etree.fromstring(response.content)

# Load and clean static radio EPG
with open(radio_epg_file, 'rb') as f:
    content = f.read().lstrip()
    radio_epg = etree.fromstring(content)

# Separate and collect all <channel> and <programme> elements
channels = dynamic_epg.findall('./channel')
programmes = dynamic_epg.findall('./programme')

# Track existing channel IDs
existing_channel_ids = {ch.get('id') for ch in channels}

# Append radio <channel> elements if not already included
for ch in radio_epg.findall('./channel'):
    cid = ch.get('id')
    if cid not in existing_channel_ids:
        channels.append(ch)
        existing_channel_ids.add(cid)

# Prepare today's midnight
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# Track all channels used in radio programmes
radio_prog_channels = set()

# Process radio programmes, repeat with 90-minute blocks
for prog in radio_epg.findall('./programme'):
    start_str = prog.get('start')
    channel = prog.get('channel')
    radio_prog_channels.add(channel)

    offset = start_str[14:] if len(start_str) > 14 else " +0000"

    for day in range(repeat_days):
        base_date = today + timedelta(days=day)

        for minutes in range(0, 24 * 60, block_minutes):
            start_dt = base_date + timedelta(minutes=minutes)
            stop_dt = start_dt + timedelta(minutes=block_minutes)

            new_prog = etree.Element('programme')
            new_prog.set('start', start_dt.strftime("%Y%m%d%H%M%S") + offset)
            new_prog.set('stop', stop_dt.strftime("%Y%m%d%H%M%S") + offset)
            new_prog.set('channel', channel)

            # Deep copy all child elements (title, desc, etc.)
            for child in prog:
                new_prog.append(copy.deepcopy(child))

            programmes.append(new_prog)

# Auto-generate <channel> for any programmes missing a definition
missing_channels = radio_prog_channels - existing_channel_ids
for cid in missing_channels:
    ch = etree.Element('channel', id=cid)
    dn = etree.Element('display-name', lang='es')
    dn.text = cid  # fallback display name
    ch.append(dn)
    channels.append(ch)
    existing_channel_ids.add(cid)

# Construct the final EPG <tv> tree
tv_root = etree.Element('tv')
for ch in channels:
    tv_root.append(ch)
for prog in programmes:
    tv_root.append(prog)

# Save the merged EPG
tree = etree.ElementTree(tv_root)
tree.write(output_file, encoding='utf-8', xml_declaration=True, pretty_print=True)

print(f"✅ Merged EPG saved to '{output_file}' with {repeat_days} day(s) of 90-minute radio programming.")