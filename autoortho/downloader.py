#!/usr/bin/env python3

import os
import re
import sys
import glob
import time
import json
import shutil
import zipfile
import argparse
from urllib.request import urlopen, Request

def do_url(url, headers={}, ):
    req = Request(url, headers=headers)
    resp = urlopen(req, timeout=5)
    if resp.status != 200:
        raise Exception
    return resp.read()


class OrthoRegion(object):
    
    region_id = None
    latest_version = 0
    ortho_size = 0
    overlay_size = 0

    local_version = -1
    download_dir = ""
    extract_dir = ""
    downloaded = False
    extracted = False
    pending_update = False

    size = 0
    download_count = 0

    def __init__(self, region_id):
        self.region_id = region_id
        self.ortho_urls = []
        self.overlay_urls = []
        self.info_dict = {}


    def __repr__(self):
        return f"OrthoRegion({self.region_id})"

    def check_local(self):
        info_dict_path = os.path.join(
            self.extract_dir,
            "z_autoortho",
            f"{self.region_id}_info.json"
        )
        if os.path.exists(info_dict_path):
            with open(info_dict_path) as h:
                info = json.loads(h.read())

            self.local_version = info.get('ver',-1)
            if self.local_version == self.latest_version:
                self.extracted = True
                self.pending_update = False
                print(f"We already have up to date {self.region_id}")
            else:
                self.pending_update = True
        else:
            self.pending_update = True


    def download(self):
        downloaded_s = set(os.listdir(self.download_dir))
        orthos_s = set(os.path.basename(x) for x in self.ortho_urls)
        overlays_s = set(os.path.basename(x) for x in self.overlay_urls)

        missing_orthos = orthos_s - downloaded_s
        missing_overlays = overlays_s - downloaded_s

        if not missing_orthos and not missing_overlays:
            self.downloaded = True
            print("All files already downloaded!")
            return

        for url in self.ortho_urls:
            if os.path.basename(url) in missing_orthos:
                print(f"Will download {url}")
                self._get_file(url, self.download_dir)
            else:
                print(f"We already have {url}")
        print("ORTHOS DOWNLOADED")

        for url in self.overlay_urls:
            if os.path.basename(url) in missing_overlays:
                print(f"Will download {url}")
                self._get_file(url, self.download_dir)
            else:
                print(f"We already have {url}")
        print("OVERLAYS DOWNLOADED")
    
        self.downloaded = True


    def _get_file(self, url, outdir):
        filename = os.path.basename(url)
        t_filename = f"{filename}.temp"
        outpath = os.path.join(outdir, t_filename)
        destpath = os.path.join(outdir, filename)

        content_len = 0
        total_fetched = 0
        chunk_size = 1024*64

        start_time = time.time()
        with urlopen(url) as d:
            content_len = int(d.headers.get('Content-Length'))
            with open(outpath, 'wb') as h:
                chunk = d.read(chunk_size)
                while chunk:
                    h.write(chunk)
                    total_fetched += len(chunk)
                    pcnt_done = (total_fetched/content_len)*100
                    MBps = (total_fetched/1048576) / (time.time() - start_time)
                    print(f"\r{pcnt_done:.2f}%   {MBps:.2f} MBps", end='')
                    chunk = d.read(chunk_size)

        os.rename(outpath, destpath)
        print("  DONE!")


    def extract(self):
        self.check_local()

        if self.extracted:
            print("Already extracted.  Skip")
            return
    
        if not self.downloaded:
            print(f"Region {self.region_id} version {self.latest_version} not downloaded!")
            return

        print(f"Ready to extract archives for {self.region_id} v{self.latest_version}!")
        
        ortho_paths = [ os.path.join(self.download_dir, os.path.basename(x))
                for x in self.ortho_urls ]

        overlay_paths = [ os.path.join(self.download_dir, os.path.basename(x))
                for x in self.overlay_urls ]

        # Split zips
        split_zips = {}
        for o in overlay_paths + ortho_paths:
            m = re.match('(.*\.zip)\.[0-9]*', o)
            if m:
                print(f"Split zip detected for {m.groups()}")
                zipname = m.groups()[0]
                print(f"ZIPNAME {zipname}")
                split_zips.setdefault(zipname, []).append(o)
                
        for zipfile_out, part_list in split_zips.items():
            # alphanumeric sort could have limits for large number of splits
            part_list.sort()
            with open(zipfile_out, 'wb') as out_h:
                for p in part_list:
                    with open(p, 'rb') as in_h:
                        out_h.write(in_h.read())

            print(f"Extracting {zipfile_out}")
            with zipfile.ZipFile(zipfile_out) as zf:
                zf.extractall(self.extract_dir)
        

        z_autoortho_path = os.path.join(self.extract_dir, "z_autoortho")
        if not os.path.exists(z_autoortho_path):
            os.makedirs(z_autoortho_path)
        

        # Normal zips
        for o in ortho_paths:
            if os.path.exists(o) and o.endswith('.zip'):
                print(f"Extracting {o}")
                with zipfile.ZipFile(o) as zf:
                    zf.extractall(self.extract_dir)
            
                orthodirs_extracted = glob.glob(
                    os.path.join(self.extract_dir, f"z_{self.region_id}_*")
                )

                for d in orthodirs_extracted:
                    shutil.copytree(
                        os.path.join(d, "Earth nav data"),
                        os.path.join(z_autoortho_path, "Earth nav data"),
                        dirs_exist_ok=True
                    )
                    shutil.copytree(
                        os.path.join(d, "terrain"),
                        os.path.join(z_autoortho_path, "terrain"),
                        dirs_exist_ok=True
                    )
                    shutil.copytree(
                        os.path.join(d, "textures"),
                        os.path.join(z_autoortho_path, "_textures"),
                        dirs_exist_ok=True
                    )
                    shutil.rmtree(d)

        for o in overlay_paths:
            if os.path.exists(o) and o.endswith('.zip'):
                print(f"Extracting {o}")
                with zipfile.ZipFile(o) as zf:
                    zf.extractall(self.extract_dir)

        if overlay_paths:
            # Setup overlays
            shutil.copytree(
                os.path.join(self.extract_dir, f"y_{self.region_id}", "yOrtho4XP_Overlays"),
                os.path.join(self.extract_dir, "yAutoOrtho_Overlays"),
                dirs_exist_ok=True
            )
            shutil.rmtree(
                os.path.join(self.extract_dir, f"y_{self.region_id}")
            )

        # Save metadata
        self.info_dict['ver'] = self.latest_version
        with open(os.path.join(
                self.extract_dir,
                "z_autoortho",
                f"{self.region_id}_info.json"
            ), 'w') as h:
                h.write(json.dumps(self.info_dict))


    def cleanup(self):
        for f in os.listdir(self.download_dir):
            os.remove(os.path.join(self.download_dir, f))


class Downloader(object):
    url = "https://api.github.com/repos/kubilus1/autoortho-scenery/releases"
    regions = {}
    region_list = ['na', 'aus_pac', 'eur']

    def __init__(self, extract_dir, download_dir="downloads"):
        self.download_dir = download_dir
        self.extract_dir = extract_dir
        
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)


    def find_releases(self):
        print("Looking for regions ...")

        resp = do_url(
            self.url,
            headers = {"Accept": "application/vnd.github+json"}
        )

        data = json.loads(resp)
        for item in data:
            v = item.get('name')
            found_regions = [ 
                re.match('(.*)_info.json', x.get('name')).groups()[0] for x in item.get('assets') if x.get('name','').endswith('_info.json') 
            ]
            
            for r in [f for f in found_regions if f not in self.regions]:
                print(f"Found region {r} version {v}")

                if r not in self.regions:
                
                    #print(f"Create region object for {r}")
                    region = OrthoRegion(r)
                    region.latest_version = v
                    region.download_dir = self.download_dir
                    region.extract_dir = self.extract_dir

                    for a in item.get('assets'):
                        asset_name = a.get('name')
                        #print(f"Add asset {asset_name}")
                        #print(a.get('name'))
                        if asset_name.endswith("_info.json"):
                            resp = do_url(a.get('browser_download_url'))
                            info = json.loads(resp)
                            region.info_dict = info
                            region.check_local()
                            #print(info)
                        elif asset_name.startswith("z_"):
                            # Found orthos
                            region.ortho_size += int(a.get('size'))
                            region.ortho_urls.append(a.get('browser_download_url'))
                        elif asset_name.startswith("y_"):
                            # Found overlays
                            region.overlay_size += int(a.get('size'))
                            region.overlay_urls.append(a.get('browser_download_url')) 
                        else:
                            print(f"Unknown file {asset_name}")
                        
                        region.size += a.get('size')

                        if a.get('download_count') >= region.download_count:
                            region.download_count = a.get('download_count')

                    self.regions[r] = region
                    #print(region)

            if len(self.regions) == len(self.region_list):
                break


    def download_region(self, region_id):
        print(f"Download {region_id}")
        r = self.regions.get(region_id)
        r.download()


    def extract(self, region_id):
        print(f"Extracting {region_id}")
        r = self.regions.get(region_id)
        r.extract()

    def cleanup(self, region_id):
        print(f"Cleaning up {region_id}")
        r = self.regions.get(region_id)
        r.cleanup()


if __name__ == "__main__":
    d = Downloader(os.path.expanduser("~/X-Plane 12/Custom Scenery"))
    d.find_releases()

    action = sys.argv[1]

    if action == 'fetch':
        region = sys.argv[2]
        d.download_region(region)
        d.extract(region)
        #d.cleanup(region)

    elif action == 'list':
        for r in d.regions.values():
            print(f"{r} current version {r.local_version}")
            if r.pending_update:
                print(f"    Available update ver: {r.latest_version}, size: {r.size/1048576:.2f} MB, downloads: {r.download_count}")

