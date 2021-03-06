# AutoOrtho - Automatic orthophotos for X-Plane 11

Orthophoto satellite imagery is something that has been supported by X-Plane
for some time.  However, this would require a large commitment of storage
space and patience since imagery would need to be downloaded and prepared
ahead of time.

This project is an attempt, and working example, of an approach to only fetch
the imagery that we need on the fly.

[![Video](https://img.youtube.com/vi/seuguds8GX0/hqdefault.jpg)](https://www.youtube.com/watch?v=seuguds8GX0)

## Quick start
Assumptions:
* You are running on Linux
* You have installed X-Plane 11.50+
* You have setup a mount point in your custom scenery and added it to the end
  of your `scenery_packs.ini` file

```
git clone https://github.com/kubilus1/autoortho
cd autoortho
python3 -m pip install -U -r requirements.txt
python3 autoortho <my orthophoto directory> <mount point in custom scenery>
```

### Experimental Windows Setup

Assumptions:
* You are running 64bit Windows 10+
* You have install X-Plane 11.50+
* You have setup and configured [WinFSP](https://github.com/winfsp/winfsp)
* You have installed a recent version of [Python](https://www.python.org/downloads/)

Setup:
* Grab the latest release zip (https://github.com/kubilus1/autoortho/releases)
  and extract somewhere
* Execute the `run.bat` file
* On first run answer the prompts.  Subsequent runs will preserve this config.

NOTES:
* WinFSP has a quirk where the mount point you choose cannot be a directory
  that already exists.
* Windows support has been tested to the extent that unit tests run.  Feedback
  on if this works at all within X-Plane one way or another would be good to hear.


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


## Usage

Install python3 and pip if you haven't already done so.  Install the
requirements:

```
python3 -m pip install -r requirements.txt
```

Prepare any orthophotos ahead of time with Ortho4XP (or any existing scenery
packs without the `.dds` files.).  These should be located *outside* your
`Custom Scenery` folder!

Create an empty directory in your `Custom Scenery` folder that you will use
for this virtual file system.  You will probably want to edit your
`scenery_packs.ini` file and add this to the appropriate location.

You will effectively now 'mount' your prepared orthophoto directory to your
`Custom Scenery` folder using this program.  Go to the location of this tool
and for example:

```
python3 autoortho <my orthophoto directory> <mount point in custom scenery>
```

Start X-Plane normally.  

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

This tool leverages fusepy and should be
compatible with any Operating System that is supported by fusepy.  

This project requires python3.x and all pre-requisites in the
`requirements.txt` file.  Also, a copy of X-Plane 11.50+ of course.

All testing is done on Ubuntu 20.04.  Other Linux flavors ought to work as
well.  MacOS very likely *should* work, but I have no way of testing it.

I have done basic testing on Windows 10 with the
[WinFSP](https://github.com/winfsp/winfsp) project.  So far this looks
promising but I have no way of fully testing this with X-Plane so your mileage
may vary.

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
* Allow for overriding the satellite source type.  Since this pulls on the
  fly, we aren't stuck with what was setup initially with Ortho4XP.
* Package a set of DSF files to get started with

## Other projects and links
* (Ortho4XP) [https://github.com/oscarpilote/Ortho4XP]
* (Slippy Mapy Tilenames) [https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames]

## Warnings, Warranty, etc

This project is provided free of charge and is not warrantied in any way.  Use
at your own risk.

Accessing map data from 3rd parties may or may not be allowed and is up to you
the end user to determine and use appropriately.
