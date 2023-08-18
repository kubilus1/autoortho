# Instructions

## Linux Setup
Assumptions:

* You have installed X-Plane 11.50+
* You have a reasonably fast CPU and broadband internet 
* FUSE is installed and setup (Enable `user_allow_other` in /etc/fuse.conf, if not already the case.) 

### Steps:

1. Download the most recent packaged release (autortho_lin_####.bin) [from here](https://github.com/kubilus1/autoortho/releases/latest)
3. Make executable if needed `chmod +x autoortho_lin.bin` 
4. Run the program `./autoortho_lin.bin`
6. Configure your X-Plane Custom Scenery directory to point to the appropriate location
7. Download and setup an ortho set from the 'Scenery' tab.
8. Click 'Run' to run the program
9. Configure your scenery_packs.ini file appropriately
10. Run X-Plane and choose a location for an ortho set you have downloaded

## Windows Setup

Assumptions:

* You are running 64bit Windows 10+
* You have install X-Plane 11.50+
* You have setup and configured [Dokan](https://github.com/dokan-dev/dokany/releases/latest)
* * NOTE: As a backup you can try [WinFSP](https://github.com/winfsp/winfsp)
    Dokan is now recommended, but some users on Windows 11 have better luck
    with WinFSP for some reason.  Make sure to fully uninstall Dokan (and
    reboot) before attempting to use WinFSP.
* You install all components, including scenery, on a local NTFS drive.

### Zip File Steps:

1. Download the most recent packaged release (autoortho_win_####.zip) [from here](https://github.com/kubilus1/autoortho/releases/latest)
2. Extract the downloaded directory.
4. Run `autoortho_win.exe` from within the extracted dir.
5. Configure your X-Plane Custom Scenery directory to point to the appropriate location
6. Download and setup an ortho set from the 'Scenery' tab.
7. Click 'Run' to run the program
8. Configure your scenery_packs.ini file appropriately 
9. Run X-Plane and choose a location for an ortho set you have downloaded

### Experimental Installer Steps:

Alternatively, there is now an installer that can be used.  This is
experimental ATM:

1. Download the most recent packaged release (AutoOrtho_####.exe) [from here](https://github.com/kubilus1/autoortho/releases/latest)
2. Run the program.
3. If there is a prior install you will be prompted to uninstall first.  Do
   this.
4. Run AutoOrtho from your system start menu.
5. Configure your X-Plane Custom Scenery directory to point to the appropriate location
6. Download and setup an ortho set from the 'Scenery' tab.
7. Click 'Run' to run the program
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
files in scenery_packs.ini.

This tool will download and setup numerous directories in your 'Custom
Scenery' folder of the form:  `z_ao_<short name of scenery pack>` and a
directory named `yAutoOrtho_Overlays`.  Typically these should be listed
towards the bottom of your scenery_packs.ini file:

```
Landmarks, airports, etc
simHeaven, special layers, etc
yAutoOrtho_Overlays
z_ao_aus_pac
z_ao_eur
z_ao_na
z_autoortho
zzz_global_scenery
```

## Installing in custom directories

It is possible to install scenery into directories other than X-Plane's Custom
Scenery directory.  

You should have a good understanding of how X-Plane handles custom scenery
before attempting this!

1. This will require that you configure AutoOrtho to point the 'Custom Scenery' setting to this alternative directory.
2. Setup and install scenery as per normal.  Run the program at least once to
   create the mount points.  You should see folder that correspond to the
   installed packages now in the alternative directory that was setup.  The
   format will look like `z_ao_XXXX`
3. You will then need to manually link each of the resulting mount directories to X-Planes's origin Custom Scenery dir.
   On Linux you can use a symlink.  On Windows you can create a shortcut.
4. Make sure Autoortho is running and start X-Plane.  Double check your
   `scenery_packs.ini` file to assure the directories are seen.


---

# Requirements and Compatibility

To run from source, this project requires python3.x and all pre-requisites in the
`requirements.txt` file.  Also, a copy of X-Plane 11.50+ of course.

Most testing is done on Ubuntu 22.04 using FUSE.  Other Linux flavors ought to work as
well.  MacOS very likely *should* work, but I have no way of testing it.

I have done testing on Windows 10 with the
[Dokan](https://github.com/dokan-dev/dokany/releases/latest) project.
This does appear to work fine, but this is not how I use this project, so it's not my primary concern.

# Known issues and limits
* Currently I try to limit the memory usage, though it's possible it
  will exceed this in certain scenarios.
* Not really possible to post-process the satellite photos.  You get what you
  get.
* Will add a couple minutes to initial flight time for new areas.  That's to
  be expected though.
* Will require and use a lot of internet requests (surprise!) and writes a lot of small files locally.  
  There are many parts along your path that may need tuning or may not like this (ISP, DNS, Wifi, drive speed, CPU speed, etc).  
  User's should be ready to diagnose their specific setup and determine if this project fits withing their own personal computing requirements.
* Windows has too many variations with how filesystems are handled, links are
  done, intrusive malware detection systems, etc and will likely always be
  slower and more difficult to use with this project.

# TODOS

* ~See if this will work on Windows with WinFSP~ 
* ~Allow for overriding the satellite source type.  Since this pulls on the fly, we aren't stuck with what was setup initially with Ortho4XP.~
* ~Package a set of DSF files to get started with~
* Attempt to make a workable OSX version

# Warnings, Warranty, etc

This project is provided free of charge and is not warrantied in any way.  Use
at your own risk.

Accessing map data from 3rd parties may or may not be allowed and is up to you
the end user to determine and use appropriately.
