#!/usr/bin/env python3

# EPG merger
# Created by:  @thefirefox12537

import re
import glob
import json
import pgzip
import shutil
import logging
import argparse
import requests
import threading
import platform, os, sys
import lxml.etree as et

parser = argparse.ArgumentParser();
parser.add_argument('--source', required=True, help='EPG source');
parser.add_argument('-o', '--output', required=True, help='EPG output');
parser.add_argument('-t', '--norm-tmp', action='store_true', help='Do not remove temporary files');
parser.add_argument('-z', '--compress', action='store_true', help='With GZip compressing');
gen_info = parser.add_argument_group('(Optional) EPG Generated Information');
gen_info.add_argument('--gen-name', help='Generated name');
gen_info.add_argument('--gen-url', help='Generated URL');
args = parser.parse_args();

tmpdir = os.environ['TEMP'] if platform.system() == 'Windows' else ('{}' if os.path.isdir('{}') else '/var{}').format('/tmp');
tmpdir = tmpdir if os.path.isdir(tmpdir) else os.sep.join(['..', 'tmp']);

epg_output = args.output + ('.gz' if args.compress else '');
epg_open = pgzip.open if args.compress else open;
epg_opt = {'mode': 'wb', 'thread': 0, 'blocksize': 2*10**8} if args.compress else {'mode': 'wb'};

def merge(tree, tagname, attrib):
  print(f'Merging {tagname}...');
  for name in files:
    file = os.sep.join([tmpdir, name]);
    try:
      srctree = et.parse(file);
      for child in srctree.getroot():
        if tagname in child.tag:
          source_dir = os.path.dirname(args.source);
          epgid = os.sep.join([source_dir, f'{name}.json']);
          if os.path.exists(epgid):
            for read in json.loads(open(epgid).read()):
              if child.attrib[attrib] == read['origin']:
                child.attrib[attrib] = read['channel_id'];
                if 'channel' == tagname:
                  found = child.find('display-name');
                  found.text = read['channel_name'];
          tree.append(child);
    except:
      print('Skipping:', file);

if __name__ == '__main__':
  urls = [];
  files = [];

  if not os.path.exists(tmpdir):
    os.makedirs(tmpdir);
  if os.path.exists(epg_output):
    os.remove(epg_output);
  if not os.path.exists(args.source):
    raise FileNotFoundError(f'{args.source} is not exist');

  with open(args.source, mode='r') as epgsrc:
    for text in re.split(r'[\r\n]+', epgsrc.read()):
      if re.findall(r'^https?://[^\s]+.xml', text):
        urls.append(text);
      elif not re.findall(r'^$', text):
        files.append(text);
  for url, name in zip(urls, files):
    epgxml = os.sep.join([tmpdir, name]);
    if not os.path.exists(epgxml):
      try:
        print(f'Downloading {name}...');
        get = requests.get(url, allow_redirects=True);
        get.raise_for_status();
        open(epgxml, mode='wb').write(get.content);
      except:
        print('Skipping download:', name);

  gen_name = args.gen_name if args.gen_name else 'cubmu';
  gen_url = args.gen_url if args.gen_url else 'cubmu.github.io';
  tree = et.Element('tv', {
    'generator-info-name': f'EPG generated by {gen_name}',
    'generator-info-url': f'https://{gen_url}'
  });
  merge(tree, tagname='channel', attrib='id');
  merge(tree, tagname='programme', attrib='channel');

  print('Parsing data...');
  et.indent(tree, space='');
  tostring = et.tostring(tree, encoding='UTF-8', method='xml', pretty_print=True);

  print('Creating file...');
  with epg_open(epg_output, **epg_opt) as epg:
    epg.write(re.sub(b'\n\n', b'', b'<?xml version="1.0" ?>\n' + tostring));
    epg.close();

  if not args.norm_tmp:
    print('Removing temporary files...');
    if tmpdir == os.sep.join(['..', 'tmp']):
      shutil.rmtree(tmpdir);
    else:
      for name in files:
        epgxml = os.sep.join([tmpdir, name]);
        if os.path.exists(epgxml):
          os.remove(epgxml);

  sys.exit();
