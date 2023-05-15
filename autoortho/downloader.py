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
import platform
import subprocess
from urllib.request import urlopen, Request
from datetime import datetime, timezone, timedelta

import logging
log = logging.getLogger(__name__)

TESTMODE=os.environ.get('AO_TESTMODE', False)
REGION_LIST = ['na', 'aus_pac', 'eur', 'sa', 'afr', 'asi']

def do_url(url, headers={}, ):
    req = Request(url, headers=headers)
    resp = urlopen(req, timeout=5)
    if resp.status != 200:
        raise Exception
    return resp.read()


class OrthoRegion(object):
   
    release_id = 0
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
    
    base_url = "https://api.github.com/repos/kubilus1/autoortho-scenery/releases"
    cur_activity = {}


    def __init__(
            self, 
            region_id, 
            release_id, 
            extract_dir="Custom Scenery", 
            download_dir="downloads", 
            release_data={},
            noclean=False
        ):

        self.region_id = region_id
        self.release_data = release_data
        self.extract_dir = extract_dir
        self.download_dir = download_dir
        self.ortho_urls = []
        self.overlay_urls = []
        self.info_dict = {}
        self.ortho_dirs = []
        self.noclean = noclean
        self.dest_ortho_dir = os.path.join(self.extract_dir, f"z_ortho_ao_{self.region_id}")

        self.rel_url = f"{self.base_url}/{release_id}"
        self.get_rel_info()
        self.check_local()

        self.cur_activity['status'] = "Idle"

    def __repr__(self):
        return f"OrthoRegion({self.region_id})"


    def get_rel_info(self):
        if not self.release_data:
            resp = do_url(
                self.rel_url,
                headers = {"Accept": "application/vnd.github+json"}
            )
            data = json.loads(resp)
        else:
            data = self.release_data

        self.latest_version = data.get('name')

        for a in data.get('assets'):
            asset_name = a.get('name')
            #log.info(f"Add asset {asset_name}")
            #log.info(a.get('name'))
            if asset_name.endswith("_info.json"):
                resp = do_url(a.get('browser_download_url'))
                info = json.loads(resp)
                self.info_dict = info
                #log.info(info)
            elif asset_name.startswith("z_"):
                # Found orthos
                self.ortho_size += int(a.get('size'))
                self.ortho_urls.append(a.get('browser_download_url'))
                if a.get('download_count') >= self.download_count:
                    self.download_count = a.get('download_count')
            elif asset_name.startswith("y_"):
                # Found overlays
                self.overlay_size += int(a.get('size'))
                self.overlay_urls.append(a.get('browser_download_url')) 
            else:
                log.info(f"Unknown file {asset_name}")
            
            self.size += a.get('size')



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
                if not self.check_scenery_dirs(info.get('ortho_dirs')):
                    log.info(f" ... Issues detected with scenery.  Recommend retrying")
                    self.extracted = False
                    self.pending_update = True
                else:
                    log.info(f" ... {self.region_id} up to date and validated.")
                    self.extracted = True
                    self.pending_update = False
            else:
                log.info(f" ... {self.region_id} update is available")
                self.pending_update = True
            
            # Current detected ortho_dirs
            self.ortho_dirs = info.get('ortho_dirs', [])

        else:
            log.info(f" ... {self.region_id} not setup yet")
            self.pending_update = True


    def check_scenery_dirs(self, ortho_dirs):
        for d in ortho_dirs:
            if os.path.exists(d):
                log.info(f"Detected partial scenery setup files.")
                return False

            if not os.path.exists(self.dest_ortho_dir):
                log.info(f"Missing final extraction dir: {self.dest_ortho_dir}")
                return False

            if os.path.dirname(d) != self.extract_dir:
                log.info(f"Installed scenery location of '{os.path.dirname(d)}' and configured scenery dir of '{self.extract_dir}' do not match!")
                return False
        return True
        

    def download(self):
        downloaded_s = set(os.listdir(self.download_dir))
        orthos_s = set(os.path.basename(x) for x in self.ortho_urls)
        overlays_s = set(os.path.basename(x) for x in self.overlay_urls)

        missing_orthos = orthos_s - downloaded_s
        missing_overlays = overlays_s - downloaded_s

        if not missing_orthos and not missing_overlays:
            self.downloaded = True
            log.info("All files already downloaded!")
            return

        for url in self.ortho_urls:
            if os.path.basename(url) in missing_orthos:
                log.info(f"Will download {url}")
                self._get_file(url, self.download_dir)
            else:
                log.info(f"We already have {url}")
        log.info("ORTHOS DOWNLOADED")

        for url in self.overlay_urls:
            if os.path.basename(url) in missing_overlays:
                log.info(f"Will download {url}")
                self._get_file(url, self.download_dir)
            else:
                log.info(f"We already have {url}")
        log.info("OVERLAYS DOWNLOADED")
    
        self.downloaded = True


    def _get_file(self, url, outdir):
        filename = os.path.basename(url)
        t_filename = f"{filename}.temp"
        outpath = os.path.join(outdir, t_filename)
        destpath = os.path.join(outdir, filename)

        self.cur_activity['status'] = f"Downloading {url}"
        
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
                    self.cur_activity['pcnt_done'] = pcnt_done
                    self.cur_activity['MBps'] = MBps
                    print(f"\r{pcnt_done:.2f}%   {MBps:.2f} MBps", end='')
                    self.cur_activity['status'] = f"Downloading {url}\n{pcnt_done:.2f}%   {MBps:.2f} MBps"
                    chunk = d.read(chunk_size)

        os.rename(outpath, destpath)
        self.cur_activity['status'] = f"DONE downloading {url}"
        log.info("  DONE!")

    def checkzip(self, zipfile):
        ret = zipfile.testzip()
        if ret:
            log.info(f"Errors detected with zipfile {zipfile}\nFirst bad file: {ret}")
            return False

        return True

    def extract(self):
        self.check_local()

        if self.extracted:
            log.info("Already extracted.  Skip")
            return
    
        if not self.downloaded:
            log.info(f"Region {self.region_id} version {self.latest_version} not downloaded!")
            return

        if self.ortho_dirs:
            log.info(f"Detected existing scenery dirs for {self.region_id}.  Cleanup first")
            self.cur_activity['status'] = f"Detected existing scenery dirs for {self.region_id}.  Cleanup first."
            for o in self.ortho_dirs:
                if os.path.exists(o):
                    shutil.rmtree(o)

        log.info(f"Ready to extract archives for {self.region_id} v{self.latest_version}!")
        self.cur_activity['status'] = f"Extracting archives for {self.region_id} v{self.latest_version}"
        
        ortho_paths = [ os.path.join(self.download_dir, os.path.basename(x))
                for x in self.ortho_urls ]

        overlay_paths = [ os.path.join(self.download_dir, os.path.basename(x))
                for x in self.overlay_urls ]

        central_textures_path = os.path.join(
                self.extract_dir, 
                "z_autoortho",
                "_textures"
        )
        if not os.path.exists(central_textures_path):
            os.makedirs(central_textures_path)


        zips = []

        # Assemble split zips
        split_zips = {}
        for o in overlay_paths + ortho_paths:
            m = re.match('(.*[.]zip)[.][0-9]*', o)
            if m:
                log.info(f"Split zip detected for {m.groups()}")
                zipname = m.groups()[0]
                log.info(f"ZIPNAME {zipname}")
                split_zips.setdefault(zipname, []).append(o)
            elif os.path.exists(o) and o.endswith('.zip'):
                zips.append(o)

        for zipfile_out, part_list in split_zips.items():
            #if os.path.exists(zipfile_out):
            #    log.info(f"{zipfile_out} already assembled.  Continue.")
            #    continue

            # alphanumeric sort could have limits for large number of splits
            part_list.sort()
            with open(zipfile_out, 'wb') as out_h:
                for p in part_list:
                    with open(p, 'rb') as in_h:
                        out_h.write(in_h.read())
            
            zips.append(zipfile_out)
            if not self.noclean:
                log.info(f"Cleaning up parts for {zipfile_out}")
                for p in part_list:
                    os.remove(p)


        # Extract zips
        for z in zips:
            self.cur_activity['status'] = f"Extracting {z}"
            try:
                with zipfile.ZipFile(z) as zf:
                    zf_dir = os.path.dirname(zf.namelist()[0])
                    if os.path.exists(os.path.join(self.extract_dir, zf_dir)):
                        log.info(f"Dir already exists.  Clean first")
                        shutil.rmtree(os.path.join(self.extract_dir, zf_dir))

                    if self.checkzip(zf):
                        zf.extractall(self.extract_dir)
                    else:
                        # Bad zip.  Clean and exit
                        raise zipfile.BadZipFile("Errors detected.")
            except zipfile.BadZipFile as err:
                log.info(f"ERROR: {err} with Zipfile {z}.  Recommend retrying")
                self.cur_activity['status'] = f"ERROR {err} with Zipfile {z}.  Recommend retrying."
                #raise Exception(f"ERROR: {err} with Zipfile {z}.  Recommend retrying")
                os.remove(z)
                return False

        # Cleanup
        for z in zips:
            if os.path.exists(z) and not self.noclean:
                log.info(f"Cleaning up parts for {z}")
                os.remove(z)


        ###########################################333
        # Arrange paths
        #
        orthodirs_extracted = glob.glob(
            os.path.join(self.extract_dir, f"z_{self.region_id}_*")
        )
        self.ortho_dirs = orthodirs_extracted


        if os.path.exists(self.dest_ortho_dir):
            print(f"{self.dest_ortho_dir} already exists.  Cleaning up first.")
            shutil.rmtree(self.dest_ortho_dir)

        for d in orthodirs_extracted:
            # Combine into one dir
            shutil.copytree(
                d,
                self.dest_ortho_dir, 
                dirs_exist_ok=True
            )
            shutil.rmtree(d)


        # Setup texture paths 
        cur_textures_path = os.path.join(self.dest_ortho_dir, "textures")
        log.info(f"Copy {cur_textures_path} to {central_textures_path}")
        if os.path.isdir(cur_textures_path):
            
            # Move all textures into a single directory
            shutil.copytree(
                cur_textures_path,
                central_textures_path,
                dirs_exist_ok=True
            )
            shutil.rmtree(cur_textures_path)

            texture_link_dir = os.path.join(
                self.extract_dir, "z_autoortho", "textures"
            )
            # Setup links for texture dirs
            if platform.system() == "Windows":
                subprocess.check_call(
                    f'mklink /J "{cur_textures_path}" "{texture_link_dir}"', 
                    shell=True
                )
            else:
                if not os.path.exists(
                    texture_link_dir
                ):
                    os.makedirs(texture_link_dir)
                os.symlink(
                    texture_link_dir,
                    cur_textures_path
                )


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


        log.info("Done with extract")
        self.cur_activity['status'] = f"Done extracting {self.region_id}"

        self.local_version = self.latest_version
        self.extracted = True
        self.pending_update = False
        self.save_metadata()
        self.check_local()

        return True


    def save_metadata(self):
        # Save metadata
        self.info_dict['ver'] = self.latest_version
        self.info_dict['ortho_dirs'] = self.ortho_dirs
        with open(os.path.join(
                self.extract_dir,
                "z_autoortho",
                f"{self.region_id}_info.json"
            ), 'w') as h:
                h.write(json.dumps(self.info_dict))


    def cleanup(self):
        self.cur_activity['status'] = f"Cleaning up downloaded files for {self.region_id}"
        for f in os.listdir(self.download_dir):
            os.remove(os.path.join(self.download_dir, f))
        self.cur_activity['status'] = f"Done with cleanup for {self.region_id}"


class Downloader(object):
    url = "https://api.github.com/repos/kubilus1/autoortho-scenery/releases"
    region_list = REGION_LIST 
    info_cache = os.path.join(os.path.expanduser("~"), ".autoortho-data", ".release_info")
    

    def __init__(self, extract_dir, download_dir=None, noclean=False):
        if not download_dir:
            download_dir = os.path.join(os.path.expanduser("~"), ".autoortho-data", "downloads")
            #from aoconfig import CFG
            #download_dir = CFG.paths.download_dir

        self.download_dir = download_dir
        self.extract_dir = extract_dir
        self.noclean = noclean
        self.regions = {}
        

        if TESTMODE:
            self.region_list.append('test')
        
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def find_releases(self):
        log.info("Looking for regions ...")
        
        if os.path.exists(self.info_cache):
            mtime = os.path.getmtime(self.info_cache)
            last_updated_date = datetime.fromtimestamp(mtime)
            log.info(f"Last release refresh time: {last_updated_date}")
        else:
            last_updated_date = datetime.fromtimestamp(0)

        data = []
        if last_updated_date < (datetime.today() - timedelta(hours=1)):
            log.info(f"Check for updates ...")
            
            try:
                resp = do_url(
                    self.url,
                    headers = {"Accept": "application/vnd.github+json"}
                )
                with open(self.info_cache, "wb") as h:
                    h.write(resp)
                data = json.loads(resp)
            except Exception as err:
                log.warning(f"Couldn't update release info {err}.")

        if not data and os.path.exists(self.info_cache):
            log.info(f"Using cache ...")
            with open(self.info_cache, "rb") as h:
                resp = h.read()
            data = json.loads(resp)


        log.info(f"Using scenery dir {self.extract_dir}")
        for item in data:
            v = item.get('name')
            rel_id = item.get('id')
            found_regions = [ 
                re.match('(.*)_info.json', x.get('name')).groups()[0] for x in item.get('assets') if x.get('name','').endswith('_info.json') 
            ]
           
            for r in [f for f in found_regions if f not in self.regions and f in self.region_list]:
                log.info(f"Found region {r} version {v}")

                if r not in self.regions:
                    #log.info(f"Create region object for {r}")
                    region = OrthoRegion(r, rel_id, self.extract_dir,
                            self.download_dir, item, noclean=self.noclean)
                    self.regions[r] = region

            if len(self.regions) == len(self.region_list):
                break


    def download_region(self, region_id):
        log.info(f"Download {region_id}")
        r = self.regions.get(region_id)
        r.download_dir = self.download_dir
        r.extract_dir = self.extract_dir
        r.download()


    def extract(self, region_id):
        log.info(f"Extracting {region_id}")
        r = self.regions.get(region_id)
        r.download_dir = self.download_dir
        r.extract_dir = self.extract_dir
        r.extract()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description = "AutoOrtho Scenery Downloader"
    )
    subparser = parser.add_subparsers(help="command", dest="command")

    parser.add_argument(
        "--scenerydir",
        "-c",
        default = "Custom Scenery",
        help = "Path to X-Plane 'Custom Scenery' directory or other install path"
    )
    parser.add_argument(
        "--noclean",
        "-n",
        action = "store_true",
        help = "Disable cleaning of files after extraction."
    )
    parser.add_argument(
        "--downloadonly",
        "-d",
        action = "store_true",
        help = "Download only, don't extract files."
    )


    parser_list = subparser.add_parser('list')
    parser_fetch = subparser.add_parser('fetch')

    if TESTMODE:
        REGION_LIST.append('test')

    parser_fetch.add_argument(
        "region",
        nargs = "?",
        choices = REGION_LIST, 
        help = "Which region to download and setup."
    )

    args = parser.parse_args()

    d = Downloader(os.path.expanduser(args.scenerydir), noclean=args.noclean)

    if args.command == 'fetch':
        d.find_releases()
        region = args.region
        d.download_region(region)
        if not args.downloadonly:
            d.extract(region)

    elif args.command == 'list':
        d.find_releases()
        for r in d.regions.values():
            log.info(f"{r} current version {r.local_version}")
            if r.pending_update:
                log.info(f"    Available update ver: {r.latest_version}, size: {r.size/1048576:.2f} MB, downloads: {r.download_count}")
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0)

