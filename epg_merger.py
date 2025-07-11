import requests
import copy
import os
from lxml import etree
from datetime import datetime, timedelta

# CONFIGURATION
dynamic_epg_url = 'http://m3u4u.com/xml/x79znkxmpc4318qygk24'
radio_epg_file = 'radioguide.xml'
iptv_epg_file = 'iptv-org/guide.xml'  # From iptv-org grab
output_file = 'guia-izzi.xml'
repeat_days = 3         # ⏳ Repeat for 3 full days
block_minutes = 240     # ⌛ 4-hour blocks

# Step 1: Fetch dynamic EPG from m3u4u
response = requests.get(dynamic_epg_url)
response.raise_for_status()
dynamic_epg = etree.fromstring(response.content)

# Step 2: Load radio EPG
with open(radio_epg_file, 'rb') as f:
    content = f.read().lstrip()
    radio_epg = etree.fromstring(content)

# Step 3: Initialize root <tv> element
channels = dynamic_epg.findall('./channel')
programmes = dynamic_epg.findall('./programme')
existing_channel_ids = {ch.get('id') for ch in channels}

# Step 4: Add missing radio channels
for ch in radio_epg.findall('./channel'):
    cid = ch.get('id')
    if cid not in existing_channel_ids:
        channels.append(ch)
        existing_channel_ids.add(cid)

# Step 5: Expand static radio programmes into repeated blocks
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
radio_prog_channels = set()

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

            for child in prog:
                copied = copy.deepcopy(child)
                if copied.tag == 'desc' and copied.text:
                    copied.text = copied.text.rstrip().removesuffix('(n)').rstrip()
                new_prog.append(copied)

            programmes.append(new_prog)

# Step 6: Add placeholder <channel> tags if needed
missing_channels = radio_prog_channels - existing_channel_ids
for cid in missing_channels:
    ch = etree.Element('channel', id=cid)
    dn = etree.Element('display-name', lang='es')
    dn.text = cid
    ch.append(dn)
    channels.append(ch)
    existing_channel_ids.add(cid)

# Step 7: Merge EPG from iptv-org guide.xml if it exists
if os.path.exists(iptv_epg_file):
    print("📦 Merging EPG from guide.xml...")

    sky_epg = etree.parse(iptv_epg_file).getroot()

    count_ch = 0
    count_prog = 0

    for ch in sky_epg.findall('./channel'):
        cid = ch.get('id')
        if cid not in existing_channel_ids:
            channels.append(copy.deepcopy(ch))
            existing_channel_ids.add(cid)
            count_ch += 1

    for prog in sky_epg.findall('./programme'):
        programmes.append(copy.deepcopy(prog))
        count_prog += 1

    print(f"✅ Added {count_ch} channels and {count_prog} programmes from IPTV org.")
else:
    print("⚠️ guide.xml not found — skipping IPTV merge.")

# Step 8: Output final merged XML
tv_root = etree.Element('tv')
for ch in channels:
    tv_root.append(ch)
for prog in programmes:
    tv_root.append(prog)

tree = etree.ElementTree(tv_root)
tree.write(output_file, encoding='utf-8', xml_declaration=True, pretty_print=True)

print(f"✅ Merged EPG saved to '{output_file}' with {repeat_days} days of 4-hour radio blocks and guide.xml merged.")