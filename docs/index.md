# Quick start

## *nix Setup
Assumptions:
* You have installed X-Plane 11.50+
* You have a recent version of Python and pip installed
* You have a reasonably fast CPU and broadband internet 

Steps:
1. Download the most recent release of this project: https://github.com/kubilus1/autoortho/releases
2. Extract to a convenient location
3. Enter the directory you extracted
4. Install all pre-reqs with `python3 -m pip install -r requirements.txt`
5. Run the project with `python3 autoortho`
6. Configure your X-Plane Custom Scenery directory to point to the appropriate location
7. Download and setup an ortho set from the 'Scenery' tab.
8. Click 'Fly' to run the program
9. Configure your scenery_packs.ini file appropriately
10. Run X-Plane and choose a location for an ortho set you have downloaded

## Windows Setup

Assumptions:
* You are running 64bit Windows 10+
* You have install X-Plane 11.50+
* You have setup and configured [WinFSP](https://github.com/winfsp/winfsp)
* You have installed a recent version of [Python](https://www.python.org/downloads/)

Steps:
1. Download the most recent release of this project: https://github.com/kubilus1/autoortho/releases
2. Extract to a convenient location
3. Enter the directory you extracted
4. Run the project by executing `run.bat`
5. Configure your X-Plane Custom Scenery directory to point to the appropriate location
6. Download and setup an ortho set from the 'Scenery' tab.
7. Click 'Fly' to run the program
8. Configure your scenery_packs.ini file appropriately 
9. Run X-Plane and choose a location for an ortho set you have downloaded

---

# Scenery Setup

## Using provided sceneries

*IMPORTANT*

The scenery packs provided with this tool that you download should be setup via the configuration utility.  This does more than simply download and extract the files.

If you do wish to manaually manipulate these scenery packs, you should review the source code (downloader.py in particular) and understand how symlinks and/or junctions work and the limitations of each.

If you manually move things around outside of the configuration utility, things very well might break!

*IMPORTANT*

## Configuring scenery_packs.ini

Any scenery added to XPlane requires being setup in the scenery_packs.ini file
located in your installs 'Custom Scenery' directory.

This file is order dependent where higher priority layers are towards the top
of the file and lower priority items are towards the bottom.

On initial run of XPlane after installing new scenery, these layers will
automatically be added to your scenery_packs.ini file, but likely in an
incorrect location.

This can result in strange issues, such as having no roads, buildings, or
trees when flying with XPlane.  If this is the case, double check the order of
files in scenery_packs.init

This tool will download and setup numerous directories in your 'Custom
Scenery' folder of the form:  `z_<short name of scenery pack>_<number>` and a
directory named `yAutoOrtho_Overlays`.  Typically these should be listed
towards the bottom of your scenery_packs.ini file:

```
Landmarks, airports, etc
simHeaven, special layers, etc
yAutoOrtho_Overlays
z_aus_pac_00
z_aus_pac_01
z_aus_pac_02
z_aus_pac_03
z_aus_pac_04
z_aus_pac_05
z_aus_pac_06
zzz_global_scenery
```
---

# Requirements and Compatibility

This project requires python3.x and all pre-requisites in the
`requirements.txt` file.  Also, a copy of X-Plane 11.50+ of course.

Most testing is done on Ubuntu 20.04 using FUSE.  Other Linux flavors ought to work as
well.  MacOS very likely *should* work, but I have no way of testing it.

I have done testing on Windows 10 with the
[WinFSP](https://github.com/winfsp/winfsp) project.  This does appear to work
fine, but this is not how I use this project, so it's not my primary concern.

# Known issues and limits
* Currently I try to limit the cache to 2GB of memory, though it's possible it
  will exceed this in certain scenarios.
* Not really possible to post-process the satellite photos.  You get what you
  get.
* Will still require properly created DSF files
* Will add a couple minutes to initial flight time for new areas.  That's to
  be expected though.


# TODOS

* ~See if this will work on Windows with WinFSP~ 
* Re-introduce a file cache for tiles purged from memory
* ~Allow for overriding the satellite source type.  Since this pulls on the fly, we aren't stuck with what was setup initially with Ortho4XP.~
* ~Package a set of DSF files to get started with~
* See if we can auto-arrange scenery_packs.ini files

# Other projects and links
* (Ortho4XP) [https://github.com/oscarpilote/Ortho4XP]
* (Slippy Mapy Tilenames) [https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames]

# Warnings, Warranty, etc

This project is provided free of charge and is not warrantied in any way.  Use
at your own risk.

Accessing map data from 3rd parties may or may not be allowed and is up to you
the end user to determine and use appropriately.
