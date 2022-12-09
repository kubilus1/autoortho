# AutoOrtho - Automatic orthophotos for X-Plane 11

Orthophoto satellite imagery is something that has been supported by X-Plane
for some time.  However, this would require a large commitment of storage
space and patience since imagery would need to be downloaded and prepared
ahead of time.

This project is an attempt, and working example, of an approach to only fetch
the imagery that we need on the fly.

[![Video](https://img.youtube.com/vi/seuguds8GX0/hqdefault.jpg)](https://www.youtube.com/watch?v=seuguds8GX0)


## Quick start

### *nix Setup
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

### Windows Setup

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

### Using provided sceneries

*IMPORTANT*

The scenery packs provided with this tool that you download should be setup via the configuration utility.  This does more than simply download and extract the files.

If you do wish to manaually manipulate these scenery packs, you should review the source code (downloader.py in particular) and understand how symlinks and/or junctions work and the limitations of each.

If you manually move things around outside of the configuration utility, things very well might break!

*IMPORTANT*

### Configuring scenery_packs.ini

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


## Approach

There does not appear to be a way to hook directly into the internal
texture loading mechanism of X-Plane via plugins.  Instead, this project acts
as a virtual file system interface for orthophoto satellite imagery.

As needed, imagery is downloaded from the indicated satellite photo sources as
areas are requested.  Imagery files are detected by naming convention of
`{row}_{col}_{maptype}_{zoomlevel}.dds`  This is the standard convention for
imagery created from Ortho4XP.

### How does X-Plane access scenery?

Let's look at how X-Plane accesses scenery.  In the install directory of
X-Plane there will be a `Custom Scenery` folder.  Under this folder there will
be a number of sub directories of scenery and a `scenery_packs.ini`
configuration file.  This is where X-Plane will look for scenery.

Under each scenery subdirectory, there will be an `Earth Nav Data` directory
that contains a number of lat-lon named subdirectories.  Under these
subdirectories will be a number of DSF files that contain instructions for
X-Plane for this set of coordinates.

These DSF files are picked up by X-Plane based on the area that you are
flying.  During flight initialization a set of these files around your takeoff
location are loaded.  While flying new DSF files will be loaded.  This loading
while flying happens asynchronously behind the scenes.

The DSF files can contain various instructions for X-Plane.  What we are
interested in for orthophotos are terrain files.  The terrain files a DSF
contains would then point to the textures requested for this terrain,
including satellite photo textures.  These files are typically `.dds` files,
though that's not always the case.

DDS files can contain multiple copies of the same texture at reduced
resolutions.  These are referred to as 'mipmaps'.  This allows X-Plane to just
pull in the minimum amount of data that is required into memory at any given
time.  Typically the maximum resolution for a texture is only required while
flying low and for close by tetxures.

### How this project leverages this setup (high level description)

This project effectively requires all the parts of normal orthophoto satellite
imagery, except for the satellite photos themselves.

Existing mechanisms to create and manage DSF files, and related terrain files,
still applies.  X-Plane continues to reference these files as per normal.

This program will detect when DDS files are accessed and read from X-Plane.
When X-Plane attempts to read a specific mipmap of a texture this program will
pull down just the minimum required data and return this data to X-Plane.
This happens behind the scenes and as far as X-Plane is concerned, it is
continuing to read a normal filesystem.

Since we only download the minimum required data, this process is relatively
efficient.

Data is cached in memory until a memory limit is reached, at which time older
data will be purged.


## Expert Usage and Overriding Default

### Warning
I highly recommend using the pre-packaged scenery packs provided with this
tool.  

However, it's entirely possible to use your own scenery, if you wish.  This
could be useful for situations where you want an area I haven't gotten to
packaging yet, or want a different zoom level that what is provided.

This should be considered an experts-only feature though and assumes:
* You are very comfortable with the command line
* You are very experienced using Ortho4XP and with installing custom scenery
* You are very familiar with filesystem concepts and managing your Operating
  System

If you don't have this experience, that's okay, but likely you will struggle
adding your own custom created scenery.  I would recommend that you
familiarize yourself with each of these listed items before proceeding.

### Adding your own created sceneries

Ready to add your own sceneries? Great!

So as mentioned above, this tool effectively overrides the 'textures'
directory that XPlane is pointing to in order to location satellite imagery
that is referrenced by a scenery pack's terrain files.

Due to how XPlane identifies terrain information, these directories have been
split up into reasonable sized pieces, which is why each provided scenery pack
has numerous numbered directories. 

However, autoorotho only mounts a single directory, under `Custom
Scenery/z_autoortho/textures`.  

How does that work then?  Simple each scenery directory provided by autoortho
just symlinks (on linux) or sets up a filesystem junction (on windows) to this
mount point!

However, sceneries that do not have satellite imagery, likely still have
coastline PNG files that must be preserved.  These are simply moved to `Custom
Scenery/z_autoortho/_textures`

You can take advantage of this setup for your own scenery that you have
packaged:
* Place your scenery in `Custom Scenery` as per normal
* Copy any existing texture files to `Custom Scenery/z_autoortho/_textures`
* Symlink, or directoy junction your scenery to `Custom
  Scenery/z_autoortho/textures`


## Ortho4XP Usage Tips

Ortho4XP can generate scenery files without downloading photos, which is
perfect for this project.  In the config set `skip_downloads` to `True`

Since this starts with low resolution imagery until you get going, I
recommend enabling `high_zl_airports`

So far I've been testing with a ZL of 16 for most tiles with increased ZL of
18 for airports.  You may have want to play around with the ZL levels for best
results.

Higher zoom levels will lead to increased resource usage and longer delays
initially starting up flights.

## Requirements and Compatibility

This project requires python3.x and all pre-requisites in the
`requirements.txt` file.  Also, a copy of X-Plane 11.50+ of course.

Most testing is done on Ubuntu 20.04 using FUSE.  Other Linux flavors ought to work as
well.  MacOS very likely *should* work, but I have no way of testing it.

I have done testing on Windows 10 with the
[WinFSP](https://github.com/winfsp/winfsp) project.  This does appear to work
fine, but this is not how I use this project, so it's not my primary concern.

## Known issues and limits
* Currently I try to limit the cache to 2GB of memory, though it's possible it
  will exceed this in certain scenarios.
* Not really possible to post-process the satellite photos.  You get what you
  get.
* Will still require properly created DSF files
* Will add a couple minutes to initial flight time for new areas.  That's to
  be expected though.

## TODOS

* ~See if this will work on Windows with WinFSP~ 
* Re-introduce a file cache for tiles purged from memory
* ~Allow for overriding the satellite source type.  Since this pulls on the fly, we aren't stuck with what was setup initially with Ortho4XP.~
* ~Package a set of DSF files to get started with~
* See if we can auto-arrange scenery_packs.ini files

## Other projects and links
* (Ortho4XP) [https://github.com/oscarpilote/Ortho4XP]
* (Slippy Mapy Tilenames) [https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames]

## Warnings, Warranty, etc

This project is provided free of charge and is not warrantied in any way.  Use
at your own risk.

Accessing map data from 3rd parties may or may not be allowed and is up to you
the end user to determine and use appropriately.
