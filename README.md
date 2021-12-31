# AutoOrtho - Automatic orthophotos for X-Plane 11

Orthophoto satellite imagery is something that has been supported by X-Plane
for some time.  However, this would require a large commitment of storage
space and patience since imagery would need to be downloaded and prepared
ahead of time.

This project is an attempt, and working example, of an approach to only fetch
the imagery that we need on the fly.

[![Video](https://img.youtube.com/vi/seuguds8GX0/hqdefault.jpg)](https://www.youtube.com/watch?v=seuguds8GX0)

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


### How this project leverages this setup (high level description)

This project effectively requires all the parts of normal orthophoto satellite
imagery, except for the satellite photos themselves.

Existing mechanisms to create and manage DSF files, and related terrain files,
still applies.  X-Plane continues to reference these files as per normal.

This program will detect when a DSF files is accessed.  The DSF file is parsed
and related terrain files are detected.  The terrain files are then parsed and
DDS files are detected.  These DDS files are then downloaded at a lower
resolution than the requested zoom level in order to maintain performance.
These files are cached on the disk and will not require re-downloading unless
deleted.

While flying, X-Plane will re-access DDS files that are nearby.  This program
will detect this access.  

Information about our flight is tracked through the UDP interface X-Plane
provides.  From this we can determine if this DDS file being requested is in
the direction we are facing, near or far, if we are going very fast, etc and
from that info determine the quality of tile we should return.  Ideally we
will pull down the maximum requested zoom level for the DDS file being
accessed.  This is then returned by the virtual file system.


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
python3 autoortho.py <my orthophoto directory> <mount point in custom scenery>
```

Start X-Plane normally.  

## Ortho4XP Usage Tips

Ortho4XP can generate scenery files without downloading photos, which is
perfect for this project.  In the config set `skip_downloads` to `True`

Since this starts with low resolution imagery until you get going, I
recommend enabling `high_zl_airports`

So far I've been testing with a ZL of 16 for most tiles with increased ZL of
17 for airports.  You may have want to play around with the ZL levels for best
results.

## Requirements and Compatibility

This tool leverages fusepy and should be
compatible with any Operating System that is supported by fusepy.  

This project requires python3.x and all pre-requisites in the
`requirements.txt` file.  Also, a copy of X-Plane 11.50+ of course.

All testing is done on Ubuntu 20.04.  Other Linux flavors ought to work as
well.  MacOS very likely *should* work, but I have no way of testing it.
Doubtful that this will work on Windows, but I also have no way of testing
that.

## Known issues and limits
* Going really really fast may lead to lag downloading files (though high
  numbers of DSF triangles seems to be the worse culprit)
* Not really possible to post-process the satellite photos.  You get what you
  get.
* FUSE doesn't seem to be supported with Windows, AFAICT, so probably won't
  ever work on that platform.  (Maybe with Cygwin or something IDK)
* Will still require properly created DSF files
* Will add a couple minutes to initial flight time for new areas.  That's to
  be expected though.

## TODOS

* Some kind of maximum cache size cleanup mechanism
* Can we somehow pull in max resolution imagery for the starting location?

## Other projects and links
* (Ortho4XP) [https://github.com/oscarpilote/Ortho4XP]
* (Slippy Mapy Tilenames) [https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames]
