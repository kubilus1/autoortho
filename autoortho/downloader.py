#!/usr/bin/env python3

import os
import re
import sys
import glob
import time
import json
import pprint
import shutil
import hashlib
import zipfile
import argparse
import platform
import subprocess
from urllib.request import urlopen, Request, urlretrieve, urlcleanup
from datetime import datetime, timezone, timedelta
from packaging import version


import logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
log = logging.getLogger(__name__)

if not log:
    print("NO LOG")
print(log)

TESTMODE=os.environ.get('AO_TESTMODE', False)
REGION_LIST = ['na', 'aus_pac', 'eur', 'sa', 'afr', 'asi']


def do_url(url, headers={}, ):
    req = Request(url, headers=headers)
    resp = urlopen(req, timeout=5)
    if resp.status != 200:
        raise Exception
    return resp.read()


cur_activity = {}


class Zip(object):
    zf = None
    hashfile = None

    def __init__(self, path):
        self.path = path
        self.files = []

    def check(self):

        if not os.path.exists(self.path):
            log.info(f"File does not exist. {self.path}")
            return False

        if self.hashfile:
            log.info(f"Found hashfile {self.hashfile} verifying ...")
            with open(self.path, "rb") as h:
                #python3.11 ziphash = hashlib.file_digest(h, "sha256")
                sha256 = hashlib.sha256()
                while True:
                    data = h.read(131072)
                    if not data:
                        break
                    else:
                        sha256.update(data)
                ziphash = sha256.hexdigest()

            with open(self.hashfile, "r") as h:
                data = h.read()
            m = re.match(r'(^[0-9A-Fa-f]+)\s+(\S.*)$', data)
            if m:
                if m.group(1) == ziphash:
                    return True

            log.error(f"Hash check failed for {self.path} : {m.group(1)} != {ziphash}")
            return False

        try:
            with zipfile.ZipFile(self.path) as zf:
                ret = zf.testzip()
                if ret:
                    log.error(f"Errors detected with zipfile {zf}\nFirst bad file: {ret}")
                    return False
        except Exception as err:
            log.error(f"Error with zip {err}")
            return False

        return True

    def __repr__(self):
        return(f"Zip({self.path})")

    def assemble(self):
        if any(x.endswith('.zip') for x in self.files):
            print(f"No assembly required for {self.path}")
            return


        self.files.sort()
        print(f"Will assemble {self.path} from parts: {self.files}")
        with open(self.path, 'wb') as out_h:
            for f in self.files:
                with open(f, 'rb') as in_h:
                    out_h.write(in_h.read())
                os.remove(f)

    def extract(self, dest):
        with zipfile.ZipFile(self.path) as zf:
            #zf_dir = os.path.dirname(zf.namelist()[0])
            #if os.path.exists(os.path.join(self.extract_dir, zf_dir)):
            #    log.info(f"Dir already exists.  Clean first")
            #    shutil.rmtree(os.path.join(self.extract_dir, zf_dir))
            zf.extractall(dest)
            

    def clean(self):
        if os.path.exists(self.path):
            os.remove(self.path)

        for f in self.files:
            if os.path.exists(f):
                os.remove(f)


class Package(object):
    name = None
    download_dir = ""
    install_dir = ""
    size = 0
    #package_url = ""

    installed = False
    downloaded = False
    #extracted = False
    cleaned = False

    download_count = 0

    #local_files = []

    zf = None
    
    def __init__(
        self,
        name,
        download_dir = "."
    ):
        self.name = name
        self.download_dir = download_dir
        self.zf = Zip(os.path.join(
            self.download_dir, f"{self.name}.zip"
        ))
        self.remote_urls = []

    def __repr__(self):
        return(f"Package: {str(self.__dict__)}")
        #return(str(self.__dict__))


    def download(self):
        if self.downloaded:
            log.info(f"Already downloaded.")
            return

        for url in self.remote_urls:
            cur_activity['status'] = f"Downloading {url}"

            filename = os.path.basename(url)
            destpath = os.path.join(self.download_dir, filename)

            if os.path.isfile(self.zf.path):
                print(f"{self.zf.path} already exists.  Skip.")
                continue

            print(f"Download {url}")
            self.dl_start_time = time.time()
            self.dl_url = url
            urlcleanup()
            local_file, headers = urlretrieve(
                url,
                destpath,
                self._show_progress
            )
            
            cur_activity['status'] = f"DONE downloading {url}"
            log.info("  DONE!")
            self.dl_start_time = None 
            self.dl_url = None
            urlcleanup()
            if destpath.endswith('sha256'):
                self.zf.hashfile = destpath
            else:
                self.zf.files.append(destpath)

        self.downloaded = True
        self.zf.assemble()

    def _show_progress(self, block_num, block_size, total_size):
        total_fetched = block_num * block_size
        pcnt_done = round(total_fetched / total_size *100,2)
        MBps = (total_fetched/1048576) / (time.time() - self.dl_start_time)
        cur_activity['pcnt_done'] = pcnt_done
        cur_activity['MBps'] = MBps
        print(f"\r{pcnt_done:.2f}%   {MBps:.2f} MBps", end='')
        cur_activity['status'] = f"Downloading {self.dl_url}\n{pcnt_done:.2f}%   {MBps:.2f} MBps"

    #def extract(self):
        #self.zf.extract(self.install_dir)
        #self.extracted = True

    def check(self):
        print(f"Checking {self.name}")
        if not self.zf.check():
            print(f"{self.name} is bad.  Cleaning up.")
            self.cleanup()
            return False
        print(f"{self.name} is good.")
        return True

    def install(self):
        if self.installed:
            return

        #self.uninstall()

        self.zf.extract(self.install_dir)
        self.installed = True

    def uninstall(self):
        #print(f"Install dir {self.install_dir}")
        if os.path.exists(self.install_dir):
            log.info(f"Dir exists.  Uninstalling {self.install_dir}")
            shutil.rmtree(self.install_dir)

    def cleanup(self):
        self.zf.clean()
        self.cleaned = True


class Release():
    
    download_dir = ""
    install_dir = ""
    totalsize = 0
    ver = 0
    url = ""
    
    install_name = ""

    installed = False
    downloaded = False
    #extracted = False
    cleaned = False
    parsed = False

    download_count = 0

    def __init__(
        self,
        name,
        install_dir = "Custom Scenery",
        release_dict = None,
        url = "",
        download_dir = "downloads",
    ):
        self.name = name
        self.install_dir = install_dir
        self.download_dir = download_dir
        self.url = url
        self.release_dict = release_dict if release_dict else {}
        self.packages = {}
        self.info_path = os.path.join(self.install_dir, "z_autoortho", f"{self.name}_info.json")
        
        if os.path.exists(self.info_path):
            self.load(self.info_path)


    def __repr__(self):
        return(f"Release({self.ver}, {self.install_dir}, {self.download_dir}, {self.url})")


    def load(self, info_path):
        with open(info_path) as h:
            info = json.loads(h.read())

        # Set attrs from info json
        for k,v in info.items():
            setattr(self, k, v)

        self.installed = True
        self.downloaded = True
        #self.extracted = True
        self.cleaned = True

    def save(self):
        info_dict = {k:v for k,v in self.__dict__.items() if k not in [
            'release_dict',
            'packages'
        ]}

        pprint.pprint(info_dict)
        with open(self.info_path, "w") as h:
            h.write(json.dumps(info_dict, indent=4))

    def parse(self):

        if self.parsed:
            return

        info = {}
        packages = []
        download_count = []

        self.version = self.release_dict.get('tag_name')
        self.prerelease = self.release_dict.get('prerelease')


        # Find info json
        for a in self.release_dict.get('assets'):
            asset_name = a.get('name')
            if asset_name.endswith("_info.json"):
                resp = do_url(a.get('browser_download_url'))
                info = json.loads(resp)
                #log.info(info)

        # Set attrs from info json
        for k,v in info.items():
            setattr(self, k, v)
        
        # Find assets
        for a in self.release_dict.get('assets'):
            asset_name = a.get('name')
            self.totalsize += int(a.get('size'))

            m = re.match(
                "(?P<pkgtype>[yz])_(?P<pkgname>.*)\.zip\.?(?P<pkgsub>\d*)",
                asset_name
            )
            if not m:
                log.info(f"Unknown file {asset_name}")
                continue

            asset_info = m.groupdict()
           
            pkgtype = asset_info.get('pkgtype')    
            pkgsub = asset_info.get('pkgsub')
            pkgname = asset_info.get('pkgname')
            
            p = self.packages.setdefault(
                f"{pkgtype}_{pkgname}",
                Package(f"{pkgtype}_{pkgname}", download_dir=self.download_dir)
            )
            
            if pkgtype == "y":
                # Overlay package
                p.install_dir = f"{self.install_dir}/y_ao_{self.id}"
            elif pkgtype == "z":
                # Ortho package
                p.install_dir = f"{self.install_dir}/z_autoortho/scenery/z_ao_{self.id}"

            p.remote_urls.append(a.get('browser_download_url'))

            download_count.append(a.get('download_count'))

        self.download_count = max(download_count)
        self.parsed = True

    
    def download(self):
        if self.downloaded:
            print(f"Already downloaded {self.name}")
            return
    
        self.parse()

        for k,v in self.packages.items():
            print(f"Downloading {k}")
            if v.check():
                print(f"Local file exists and is valid.")
                continue 

            v.download()
            if not v.check():
                v.download()
                v.check()

    def install(self):
        if self.installed:
            print(f"Already installed {self.name}")
            return

        print(f"Check for existing installs..")
        for k,v in self.packages.items():
            v.uninstall()

        self.parse()
        for k,v in self.packages.items():
            print(f"Installing {k}")
            if not v.check():
                print(f"{k} fails checks!")
            v.install()
        self.save()

    def cleanup(self):
        if self.cleaned:
            return

        for k,v in self.packages.items():
            print(f"Cleaning {k}")
            v.cleanup()



class Region(object):

    local_version = '0.0.0'

    def __init__(self, region_id):
        self.region_id = region_id
        self.releases = {}

    def __repr__(self):
        return(f"Region({self.region_id})")

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
        self.dest_ortho_dir = os.path.join(
            self.extract_dir,
            "z_autoortho",
            "scenery",
            f"z_ao_{self.region_id}"
        )
        self.scenery_extract_path = os.path.join(
                self.extract_dir, 
                "z_autoortho",
                "scenery"
        )

        self.rel_url = f"{self.base_url}/{release_id}"
        self.get_rel_info()
        self.check_local()

        cur_activity['status'] = "Idle"

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
        destpath = os.path.join(outdir, filename)
        
        cur_activity['status'] = f"Downloading {url}"
        self.dl_start_time = time.time()
        self.dl_url = url
        urlcleanup()
        local_file, headers = urlretrieve(
            url,
            destpath,
            self.show_progress
        )
        cur_activity['status'] = f"DONE downloading {url}"
        log.info("  DONE!")
        self.dl_start_time = None 
        self.dl_url = None
        urlcleanup()

    def show_progress(self, block_num, block_size, total_size):
        total_fetched = block_num * block_size
        pcnt_done = round(total_fetched / total_size *100,2)
        MBps = (total_fetched/1048576) / (time.time() - self.dl_start_time)
        cur_activity['pcnt_done'] = pcnt_done
        cur_activity['MBps'] = MBps
        print(f"\r{pcnt_done:.2f}%   {MBps:.2f} MBps", end='')
        cur_activity['status'] = f"Downloading {self.dl_url}\n{pcnt_done:.2f}%   {MBps:.2f} MBps"


    def checkzip(self, zipfile, hashfile=None):
        if os.path.isfile(hashfile):
            log.info(f"Found hashfile {hashfile} verifying ...")
            with open(zipfile.filename, "rb") as h:
                #python3.11 ziphash = hashlib.file_digest(h, "sha256")
                sha256 = hashlib.sha256()
                while True:
                    data = h.read(131072)
                    if not data:
                        break
                    else:
                        sha256.update(data)
                ziphash = sha256.hexdigest()

            with open(hashfile, "r") as h:
                data = h.read()
            m = re.match(r'(^[0-9A-Fa-f]+)\s+(\S.*)$', data)
            if m:
                if m.group(1) == ziphash and m.group(2) == os.path.basename(zipfile.filename):
                    return True

            log.error(f"Hash check failed for {zipfile.filename} : {m.group(1)} != {ziphash}")
            return False


        ret = zipfile.testzip()
        if ret:
            log.error(f"Errors detected with zipfile {zipfile}\nFirst bad file: {ret}")
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
            cur_activity['status'] = f"Detected existing scenery dirs for {self.region_id}.  Cleanup first."
            for o in self.ortho_dirs:
                if os.path.exists(o):
                    shutil.rmtree(o)

        log.info(f"Ready to extract archives for {self.region_id} v{self.latest_version}!")
        cur_activity['status'] = f"Extracting archives for {self.region_id} v{self.latest_version}"
        
        ortho_paths = [ os.path.join(self.download_dir, os.path.basename(x))
                for x in self.ortho_urls ]

        overlay_paths = [ os.path.join(self.download_dir, os.path.basename(x))
                for x in self.overlay_urls ]

        
        if not os.path.exists(self.scenery_extract_path):
            os.makedirs(self.scenery_extract_path)


        zips = []

        # Assemble split zips
        split_zips = {}
        for o in overlay_paths + ortho_paths:
            m = re.match('(.*[.]zip)[.][0-9]+', o)
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

        badzips = []
        # Check zips
        for z in zips:
            log.info(f"Checking {z}...")
            hashfile = f"{z}.sha256"
            cur_activity['status'] = f"Checking {z}"
            try:
                with zipfile.ZipFile(z) as zf:
                    zf_dir = os.path.dirname(zf.namelist()[0])

                    if self.checkzip(zf, hashfile):
                        log.info(f"{z} is good.") 
                    else:
                        # Bad zip.  Clean and exit
                        raise zipfile.BadZipFile("Errors detected.")
            except zipfile.BadZipFile as err:
                log.error(f"ERROR: {err} with Zipfile {z}.  Recommend retrying")
                cur_activity['status'] = f"ERROR {err} with Zipfile {z}.  Recommend retrying."
                #raise Exception(f"ERROR: {err} with Zipfile {z}.  Recommend retrying")
                os.remove(z)
                if os.path.exists(hashfile):
                    os.remove(hashfile)

                badzips.append(z)
                #return False

        if badzips:
            MSG = f"ERROR: Bad zips detected {badzips}.  Recommend retrying"
            log.error(MSG)
            cur_activity['status'] = MSG 
            return False


        # Extract zips
        for z in zips:
            log.info(f"Extracting {z}...")
            cur_activity['status'] = f"Extracting {z}"
                
            with zipfile.ZipFile(z) as zf:
                zf_dir = os.path.dirname(zf.namelist()[0])
                if os.path.exists(os.path.join(self.extract_dir, zf_dir)):
                    log.info(f"Dir already exists.  Clean first")
                    shutil.rmtree(os.path.join(self.extract_dir, zf_dir))
                zf.extractall(self.extract_dir)


        # Cleanup
        for z in zips:
            if os.path.exists(z) and not self.noclean:
                log.info(f"Cleaning up parts for {z}")
                os.remove(z)
            hashfile = f"{z}.sha256"
            if os.path.exists(hashfile) and not self.noclean:
                log.info(f"Cleaning up hashfile for {hashfile}")
                os.remove(hashfile)

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
            log.info(f"Setting up directories ... {d}")
            cur_activity['status'] = f"Setting up directories ... {d}"
            # Combine into one dir
            shutil.copytree(
                d,
                self.dest_ortho_dir, 
                dirs_exist_ok=True
            )
            shutil.rmtree(d)


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
        cur_activity['status'] = f"Done extracting {self.region_id}"

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
        cur_activity['status'] = f"Cleaning up downloaded files for {self.region_id}"
        for f in os.listdir(self.download_dir):
            os.remove(os.path.join(self.download_dir, f))
        cur_activity['status'] = f"Done with cleanup for {self.region_id}"


class OrthoManager(object):
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
            self.region_list.extend([f"test_{r}" for r in self.region_list])
            self.region_list.append('test')

        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)


    def _get_release_data(self):
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
        
        return data


    def find_releases(self):

        log.info("Checking local")
        local_rel_info = glob.glob(os.path.join(
            self.extract_dir, "z_autoortho", "*_info.json"
        ))
        
        for rel in [ os.path.basename(rel) for rel in local_rel_info ]:
            rel_name = re.match('(.*)_info.json', rel).groups()[0]

            release = Release(
                name = rel_name,
                install_dir = self.extract_dir,
                download_dir = self.download_dir,
            )

            region = self.regions.setdefault(
                rel_name,
                Region(rel_name)
            )
            if release.ver not in region.releases:
                region.releases[release.ver] = release
            region.local_version = release.ver
            #self.regions[release.id] = region

        log.info("Looking for available regions ...")
        
        rel_data = self._get_release_data()

        log.info(f"Using scenery dir {self.extract_dir}")
        for item in rel_data:
            rel_ver = item.get('name')
            rel_id = item.get('id')

            found_regions = [ 
                re.match('(.*)_info.json', x.get('name')).groups()[0] for x in item.get('assets') if x.get('name','').endswith('_info.json') 
            ]
            if not found_regions:
                continue

            region_name = found_regions[0]
            
            region = self.regions.setdefault(
                region_name,
                Region(region_name)
            )

            if rel_ver not in region.releases:
                release = Release(
                    name = region_name,
                    install_dir = self.extract_dir,
                    download_dir = self.download_dir,
                    url = f"{self.url}/{rel_id}",
                    release_dict = item
                )
                release.ver = rel_ver
                #release.parse()
                region.releases[rel_ver] = release
                #print(region.releases)
           
            #self.regions[region_name] = region
        
        #pprint.pprint(self.regions)
        for region in self.regions.values():
            region.releases = sorted(
                region.releases.values(), 
                key=lambda x: version.parse(x.ver),
                reverse=True
            )

    def _find_releases(self):
        log.info("Looking for regions ...")
        
        data = self._get_release_data()

        log.info(f"Using scenery dir {self.extract_dir}")
        for item in data:
            v = item.get('name')
            rel_id = item.get('id')
            found_regions = [ 
                re.match('(.*)_info.json', x.get('name')).groups()[0] for x in item.get('assets') if x.get('name','').endswith('_info.json') 
            ]
          
            for r in [f for f in found_regions if f not in self.regions and f in self.region_list]:
                log.info(f"Found region {r} version {v}")

                #if r not in self.regions:
                    #log.info(f"Create region object for {r}")

                if TESTMODE:
                    r = r.removeprefix('test_')

                region = OrthoRegion(r, rel_id, self.extract_dir,
                        self.download_dir, item, noclean=self.noclean)
                self.regions[r] = region

            if len(self.regions) == len(self.region_list):
                break


    def download_region_latest(self, region_id):
        log.info(f"Download {region_id}")
        r = self.regions.get(region_id)
        print(r)
        #r.download_dir = self.download_dir
        #r.extract_dir = self.extract_dir
        release = r.releases[0]
        print(release)
        release.download()


    def install(self, region_id):
        log.info(f"Extracting {region_id}")
        r = self.regions.get(region_id)
        #r.download_dir = self.download_dir
        #r.extract_dir = self.extract_dir
        #r.extract()
        print(r)
        release = r.releases[0]
        print(release)
        #release.uninstall()
        release.install()


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

    d = OrthoManager(os.path.expanduser(args.scenerydir), noclean=args.noclean)

    if args.command == 'fetch':
        d.find_releases()
        region = args.region
        d.download_region(region)
        if not args.downloadonly:
            d.install(region)

    elif args.command == 'list':
        d.find_releases()
        for r in d.regions.values():
            print(f"{r} current version {r.local_version}")
            log.info(f"{r} current version {r.local_version}")
            #if r.pending_update:
            #    log.info(f"    Available update ver: {r.latest_version}, size: {r.size/1048576:.2f} MB, downloads: {r.download_count}")
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0)

