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

# Collect all channels and programmes separately
channels = []
programmes = []

# Add dynamic channels and programmes
channels.extend(dynamic_epg.findall('./channel'))
programmes.extend(dynamic_epg.findall('./programme'))

# Track existing channel ids to avoid duplicates
existing_channel_ids = {ch.get('id') for ch in channels}

# Add radio channels (avoid duplicates)
for ch in radio_epg.findall('./channel'):
    cid = ch.get('id')
    if cid not in existing_channel_ids:
        channels.append(ch)
        existing_channel_ids.add(cid)

# Prepare today's midnight for programme time calculations
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# Keep track of radio programme channels (for generating missing <channel> elements)
radio_prog_channels = set()

# Process radio programmes with 90-minute durations and add repeats
for prog in radio_epg.findall('./programme'):
    start_str = prog.get('start')
    channel = prog.get('channel')
    radio_prog_channels.add(channel)

    start_time = datetime.strptime(start_str[:14], "%Y%m%d%H%M%S").time()
    offset = start_str[14:] if len(start_str) > 14 else "+0000"

    for day in range(repeat_days):
        base_date = today + timedelta(days=day)
        start_dt = datetime.combine(base_date, start_time)
        stop_dt = start_dt + timedelta(minutes=90)
        if stop_dt <= start_dt:
            stop_dt += timedelta(days=1)

        new_prog = etree.Element('programme')
        new_prog.set('start', start_dt.strftime("%Y%m%d%H%M%S") + offset)
        new_prog.set('stop', stop_dt.strftime("%Y%m%d%H%M%S") + offset)
        new_prog.set('channel', channel)

        for child in prog:
            new_prog.append(child)

        programmes.append(new_prog)

# Auto-generate missing <channel> elements for any programme channels missing a channel entry
missing_channels = radio_prog_channels - existing_channel_ids
for cid in missing_channels:
    ch = etree.Element('channel', id=cid)
    dn = etree.Element('display-name', lang='es')
    dn.text = cid
    ch.append(dn)
    channels.append(ch)
    existing_channel_ids.add(cid)

# Build new <tv> root and append all channels and programmes in correct order
tv_root = etree.Element('tv')
for ch in channels:
    tv_root.append(ch)
for prog in programmes:
    tv_root.append(prog)

# Save merged EPG
tree = etree.ElementTree(tv_root)
tree.write(output_file, encoding='utf-8', xml_declaration=True, pretty_print=True)

print(f"✅ Merged EPG saved to '{output_file}' with {repeat_days} days of 90-minute radio programming.")