#!/usr/bin/env python3

import argparse
import glob
import hashlib
import json
import logging
import os
import pprint
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime, timedelta
from urllib.request import urlopen, Request, urlretrieve, urlcleanup

from packaging import version

from aoconfig import CFG

log = logging.getLogger(__name__)

TESTMODE = os.environ.get('AO_TESTMODE', False)


def do_url(url, headers={}, ):
    req = Request(url, headers=headers)
    resp = urlopen(req, timeout=5)
    if resp.status != 200:
        raise Exception
    return resp.read()


cur_activity = {}


class Zip(object):
    # A zip object that may be made up of one or more files

    zf = None
    hashfile = ''
    assembled = False

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
                # python3.11 ziphash = hashlib.file_digest(h, "sha256")
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
        return (f"Zip({self.path})")

    def assemble(self):
        if any(x.endswith('.zip') for x in self.files) or self.assembled:
            log.info(f"No assembly required for {self.path}")
            return

        self.files.sort()
        log.info(f"Will assemble {self.path} from parts: {self.files}")
        with open(self.path, 'wb') as out_h:
            for f in self.files:
                with open(f, 'rb') as in_h:
                    out_h.write(in_h.read())
                log.info(f"Removing {f}")
                os.remove(f)

        self.assembled = True

    def extract(self, dest):
        with zipfile.ZipFile(self.path) as zf:
            zf.extractall(dest)

    def clean(self):
        if os.path.exists(self.path):
            log.info(f"Removing {self.path}")
            os.remove(self.path)

        for f in self.files:
            if os.path.exists(f):
                log.info(f"Removing {f}")
                os.remove(f)

        if os.path.exists(self.hashfile):
            log.info(f"Removing {self.hashfile}")
            os.remove(self.hashfile)

        self.files = []
        self.assembled = False


class Package(object):
    # A package asset

    name = None
    download_dir = ""
    install_dir = ""
    size = 0

    installed = False
    downloaded = False
    cleaned = False

    download_count = 0

    zf = None

    def __init__(
            self,
            name,
            pkgtype,
            download_dir="."
    ):
        self.name = name
        self.pkgtype = pkgtype
        self.download_dir = download_dir
        self.zf = Zip(os.path.join(
            self.download_dir, f"{self.name}.zip"
        ))
        self.remote_urls = []

    def __repr__(self):
        return (f"Package: {str(self.__dict__)}")
        # return(str(self.__dict__))

    def download(self):
        if self.downloaded:
            log.info(f"Already downloaded.")
            return

        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

        for url in self.remote_urls:
            cur_activity['status'] = f"Downloading {url}"

            filename = os.path.basename(url)
            destpath = os.path.join(self.download_dir, filename)

            # if os.path.isfile(self.zf.path):
            if os.path.isfile(destpath):
                log.info(f"{destpath} already exists.  Skip.")
                # print(f"{self.zf.path} already exists.  Skip.")
                # self.zf.assembled = True
                # self.downloaded = True
                # return
                # continue
            else:
                log.info(f"Download {url}")
                self.dl_start_time = time.time()
                self.dl_url = url
                urlcleanup()
                local_file, headers = urlretrieve(
                    url,
                    destpath,
                    self._show_progress
                )

                cur_activity['status'] = f"DONE downloading {url}"
                log.debug("  DONE!")
                self.dl_start_time = None
                self.dl_url = None
                urlcleanup()

            if destpath.endswith('sha256'):
                self.zf.hashfile = destpath
            else:
                # elif not self.zf.assembled:
                self.zf.files.append(destpath)

        self.downloaded = True
        self.zf.assemble()

    def _show_progress(self, block_num, block_size, total_size):
        total_fetched = block_num * block_size
        pcnt_done = round(total_fetched / total_size * 100, 2)
        elapsed = time.time() - self.dl_start_time
        if not elapsed:
            return
        MBps = (total_fetched / 1048576) / elapsed
        cur_activity['pcnt_done'] = pcnt_done
        cur_activity['MBps'] = MBps
        if block_num % 1000 == 0:
            print(f"\r{pcnt_done:.2f}%   {MBps:.2f} MBps", end='')
        cur_activity['status'] = f"Downloading {self.dl_url}\n{pcnt_done:.2f}%   {MBps:.2f} MBps"

    def check(self):
        log.info(f"Checking {self.name}")
        if not self.zf.check():
            log.warning(f"{self.name} is bad.  Cleaning up.")
            self.cleanup()
            self.downloaded = False
            # self.zf.assembled = False
            return False
        log.info(f"{self.name} is good.")
        return True

    def install(self):
        if self.installed:
            return

        # self.uninstall()

        self.zf.extract(self.install_dir)

        if self.pkgtype == 'z':
            dirs = [os.path.join(self.install_dir, self.name)]
            # dirs = glob.glob(
            #    os.path.join(self.install_dir, "z_*")
            # )

        elif self.pkgtype == 'y':
            dirs = glob.glob(
                os.path.join(self.install_dir, "y_*", "yOrtho4XP_Overlays")
            )

        for d in dirs:
            # Setup files
            shutil.copytree(
                d,
                os.path.join(self.install_dir),
                dirs_exist_ok=True
            )
            shutil.rmtree(d)

        self.installed = True

    def uninstall(self):
        # print(f"Install dir {self.install_dir}")
        if os.path.exists(self.install_dir):
            log.info(f"Dir exists.  Uninstalling {self.install_dir}")
            shutil.rmtree(self.install_dir)
        self.installed = False

    def cleanup(self):
        self.zf.clean()
        self.cleaned = True
        self.downloaded = False


class Release(object):
    # A release of orthos

    download_dir = ""
    install_dir = ""
    totalsize = 0
    ver = "0.0.0"
    url = ""

    install_name = ""

    installed = False
    downloaded = False
    cleaned = False
    parsed = False
    legacy = False

    download_count = 0
    info_ver = "v2"

    def __init__(
            self,
            name,
            install_dir="Custom Scenery",
            release_dict=None,
            url="",
            download_dir="downloads",
    ):
        self.name = name
        self.install_dir = install_dir
        self.download_dir = download_dir
        self.url = url
        self.release_dict = release_dict if release_dict else {}
        self.packages = {}
        self.info_path = os.path.join(self.install_dir, "z_autoortho", f"{self.name}_info.json")
        self.ortho_dirs = []
        self.info_ver = "v2"

        # if os.path.exists(self.info_path):
        #    self.load(self.info_path)

    def __repr__(self):
        return (f"Release({self.ver}, {self.info_ver}, {self.url})")
        # return(f"Release({self.ver}, {self.install_dir}, {self.download_dir}, {self.url})")

    def load(self, info_path):
        log.info(f"Loading local info from {info_path}")
        with open(info_path) as h:
            info = json.loads(h.read())

        # Set attrs from info json
        for k, v in info.items():
            setattr(self, k, v)

        self.installed = True
        self.downloaded = True
        self.cleaned = True

        detected_info_ver = info.get('info_ver')
        if self.ortho_dirs and detected_info_ver is None:
            # We have ortho_dirs but no detected info_ver.  This is v1
            log.info(f"Legacy release detected for {self.name}")
            self.info_ver = "v1"
            self.ver = "0.0.0"
            # self.downloaded = False
            # self.installed = False
            # self.cleaned = False
            self.legacy = True
        elif detected_info_ver:
            self.info_ver = detected_info_ver

    def save(self):
        log.info(f"Saving info to {self.info_path}")
        log.debug(self.__dict__.keys())
        info_dict = {k: v for k, v in self.__dict__.items() if k not in [
            'release_dict',
            'packages'
        ]}

        pprint.pprint(info_dict)
        with open(self.info_path, "w") as h:
            h.write(json.dumps(info_dict, indent=4, default=vars))

    def parse(self):
        log.info(f"Begin parsing info_dict for {self.name}")

        if self.parsed:
            return

        info = {}
        packages = []
        download_count = []

        # self.version = self.release_dict.get('tag_name')
        self.prerelease = self.release_dict.get('prerelease')

        # if self.info_ver == 'v1':
        #    log.info(f"Legacy release detected for {self.name}")

        # Find info json
        for a in self.release_dict.get('assets', []):
            asset_name = a.get('name')
            if asset_name.endswith("_info.json"):
                resp = do_url(a.get('browser_download_url'))
                info = json.loads(resp)
                # log.info(info)

        # Set attrs from info json
        for k, v in info.items():
            setattr(self, k, v)

        # Find assets
        for a in self.release_dict.get('assets', []):
            asset_name = a.get('name')
            self.totalsize += int(a.get('size'))

            m = re.match(
                "(?P<pkgtype>[yz])_(?P<pkgname>.*)\.zip\.?(?P<pkgsub>\d*)",
                asset_name
            )
            if not m:
                log.debug(f"Unknown file {asset_name}")
                continue

            asset_info = m.groupdict()

            pkgtype = asset_info.get('pkgtype')
            pkgsub = asset_info.get('pkgsub')
            pkgname = asset_info.get('pkgname')

            p = self.packages.setdefault(
                f"{pkgtype}_{pkgname}",
                Package(
                    f"{pkgtype}_{pkgname}",
                    pkgtype,
                    download_dir=self.download_dir
                )
            )

            if pkgtype == "y":
                # Overlay package
                # p.install_dir = f"{self.install_dir}/y_ao_{self.id}"
                p.install_dir = f"{self.install_dir}/yAutoOrtho_Overlays"
            elif pkgtype == "z":
                # Ortho package
                p.install_dir = f"{self.install_dir}/z_autoortho/scenery/z_ao_{self.id}"

            p.remote_urls.append(a.get('browser_download_url'))
            download_count.append(a.get('download_count'))

        if download_count:
            self.download_count = max(download_count)
        self.parsed = True

    def download(self):
        if self.downloaded:
            log.info(f"Already downloaded {self.name}")
            return True

        self.cleaned = False
        self.parse()

        for k, v in self.packages.items():
            log.info(f"Downloading {k}")
            # if v.check():
            #    log.info(f"Local file exists and is valid.")
            #    continue 

            v.download()
            if not v.check():
                log.warning(f"{k} failed checks.  Retrying ...")
                v.download()
                if not v.check():
                    log.error(f"{k} failed again.  Exiting!")
                    return False

        self.downloaded = True
        return True

    def install(self):
        if self.installed:
            log.info(f"Already installed {self.name}")
            return True

        print(f"Check for and cleanup existing installs..")
        for k, v in self.packages.items():
            if v.pkgtype == "z":
                log.debug("Must cleanup ortho type package.")
                v.uninstall()

        self.parse()
        for k, v in self.packages.items():
            log.info(f"Installing {k}")
            if not v.check():
                log.warning(f"{k} fails checks!")
                self.downloaded = False
                return False
                # continue
            v.install()
        self.save()
        self.installed = True
        self.cleanup()
        return True

    def cleanup(self):
        if self.cleaned:
            return

        for k, v in self.packages.items():
            print(f"Cleaning {k}")
            v.cleanup()
        self.cleaned = True

    def uninstall(self):
        # self.cleanup()
        # log.info(f"Removing {self.install_dir}")
        # shutil.rmtree(self.install_dir)
        for o in self.ortho_dirs:
            if os.path.exists(o):
                log.info(f"Removing {o}")
                shutil.rmtree(o)

        legacy_dirs = [
            os.path.join(self.install_dir, "z_autoortho", "textures"),
            os.path.join(self.install_dir, "z_autoortho", "_textures")
        ]
        for l in legacy_dirs:
            if os.path.exists(l):
                shutil.rmtree(l)

        # for k,v in self.packages.items():
        #     log.debug(v)
        #     log.info(f"Uninstall package: {k}")
        #     v.uninstall()

        self.installed = False
        # self.downloaded = False


class Region(object):
    # A Particular region of orthos and/or overlays

    # local_version = '0.0.0'
    local_rel = None

    def __init__(self, region_id, install_dir=".", download_dir="."):
        self.region_id = region_id
        self.releases = {}
        self.install_dir = install_dir
        self.download_dir = download_dir
        self.find_existing()

    def __repr__(self):
        return (f"Region({self.region_id})")

    def find_existing(self):
        log.info(f"Checking installed releases for {self.region_id}")
        local_rel_info = glob.glob(os.path.join(
            self.install_dir, "z_autoortho", f"{self.region_id}_info.json"
        ))

        for rel in [os.path.basename(rel) for rel in local_rel_info]:
            rel_name = re.match('(.*)_info.json', rel).groups()[0]
            log.info(f"Found local info file for {rel_name}")

            release = Release(
                name=rel_name,
                install_dir=self.install_dir,
                download_dir=self.download_dir,
            )
            # Load local info from _info.json
            release.load(release.info_path)

            if release.legacy:
                log.info(f"{rel} is a legacy release.")

            if release.ver not in self.releases:
                self.releases[release.ver] = release

            self.local_rel = release
            # self.local_version = release.ver
            # self.regions[release.id] = region

    def get_latest_release(self):
        releases = sorted(
            self.releases.values(),
            key=lambda x: version.parse(x.ver),
            reverse=True
        )
        log.debug(f"SORTED: {releases}")
        return releases[0]

    def install_release(self, ver=None):

        if ver is None:
            rel = self.get_latest_release()
        else:
            rel = self.releases[ver]

        if self.local_rel and self.local_rel.ver == rel.ver:
            log.info(f"Requested version: {rel.ver} is already installed.")
            return
        elif self.local_rel:
            log.info("Local release detected.  Uninstalling...")
            self.local_rel.uninstall()
            self.releases.pop(self.local_rel.ver)
            self.local_rel = None

        if not rel.download():
            log.error(f"Failed to download release {rel}")
            return False

        if not rel.install():
            log.error(f"Failed to install release {rel}")
            return False

        return True


class OrthoManager(object):
    url = "https://api.github.com/repos/kubilus1/autoortho-scenery/releases"
    info_cache = os.path.join(os.path.expanduser("~"), ".autoortho-data", ".release_info")

    def __init__(self, extract_dir=None, download_dir=None, noclean=False):
        if not download_dir:
            download_dir = CFG.paths.download_dir
            # download_dir = os.path.join(os.path.expanduser("~"), ".autoortho-data", "downloads")
        if not extract_dir:
            extract_dir = CFG.paths.scenery_path

        self.download_dir = download_dir
        self.extract_dir = extract_dir
        self.noclean = noclean
        self.regions = {}

        overlay_list = []

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
                    headers={"Accept": "application/vnd.github+json"}
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

    def find_regions(self):
        log.info(f"Looking for available regions ...")

        rel_data = self._get_release_data()

        log.info(f"Using scenery dir {self.extract_dir}")
        for item in rel_data:
            rel_ver = item.get('name')
            rel_id = item.get('id')

            # log.debug(f"VER: {rel_ver}, ID: {rel_id}")
            found_regions = [
                re.match('(.*)_info.json', x.get('name')).groups()[0] for x in item.get('assets') if
                x.get('name', '').endswith('_info.json')
            ]
            if not found_regions:
                continue

            region_name = found_regions[0]

            prerelease = item.get('prerelease')
            if prerelease and not TESTMODE:
                log.debug(f"{region_name}:{rel_ver} is pre-release. skipping.")
                continue

            if region_name not in self.regions:
                region = Region(
                    region_name,
                    install_dir=self.extract_dir,
                    download_dir=self.download_dir
                )
                self.regions[region_name] = region
            else:
                region = self.regions.get(region_name)

            if rel_ver not in region.releases:
                log.debug(f"Adding new release {rel_ver} to region {region_name}")
                release = Release(
                    name=region_name,
                    install_dir=self.extract_dir,
                    download_dir=self.download_dir,
                    url=f"{self.url}/{rel_id}",
                    release_dict=item
                )
                release.ver = rel_ver
                # release.parse()
                region.releases[rel_ver] = release
                # print(region.releases)
            # log.debug(region.releases)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    parser = argparse.ArgumentParser(
        description="AutoOrtho Scenery Downloader"
    )
    subparser = parser.add_subparsers(help="command", dest="command")

    parser.add_argument(
        "--scenerydir",
        "-c",
        # default = "Custom Scenery",
        default=CFG.paths.scenery_path,
        help="Path to X-Plane 'Custom Scenery' directory or other install path"
    )
    parser.add_argument(
        "--downloaddir",
        "-d",
        default=CFG.paths.download_dir,
        help="Scenery temp download dir"
    )
    parser.add_argument(
        "--noclean",
        "-n",
        action="store_true",
        help="Disable cleaning of files after extraction."
    )
    parser.add_argument(
        "--downloadonly",
        "-o",
        action="store_true",
        help="Download only, don't extract files."
    )

    parser_list = subparser.add_parser('list')
    parser_fetch = subparser.add_parser('fetch')

    parser_fetch.add_argument(
        "region",
        nargs="?",
        # choices = REGION_LIST,
        help="Which region to download and setup."
    )

    args = parser.parse_args()

    d = OrthoManager(
        os.path.expanduser(args.scenerydir),
        os.path.expanduser(args.downloaddir),
        noclean=args.noclean
    )

    if args.command == 'fetch':
        d.find_regions()
        region = args.region
        r = d.regions.get(region)
        rel = r.get_latest_release()
        rel.download()
        # d.download_region(region)
        if not args.downloadonly:
            # d.install(region)
            r.install_release()

    elif args.command == 'list':
        d.find_regions()
        for r in d.regions.values():
            rel = r.get_latest_release()
            rel.parse()
            localinfo = ""
            if r.local_rel:
                localinfo = f" ... installed {r.local_rel.name} version: {r.local_rel.ver}"
            log.info(f"{r.region_id} latest version: {rel.name} {rel.ver} {localinfo}")
            # print(f"{r} current version {r.local_version}")
            # log.info(f"{r} current version {r.local_version}")
            # if r.pending_update:
            #    log.info(f"    Available update ver: {r.latest_version}, size: {r.size/1048576:.2f} MB, downloads: {r.download_count}")
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0)
