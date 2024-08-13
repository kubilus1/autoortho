# Approach

There does not appear to be a way to hook directly into the internal
texture loading mechanism of X-Plane via plugins.  Instead, this project acts
as a virtual file system interface for orthophoto satellite imagery.

As needed, imagery is downloaded from the indicated satellite photo sources as
areas are requested.  Imagery files are detected by naming convention of
`{row}_{col}_{maptype}_{zoomlevel}.dds`  This is the standard convention for
imagery created from Ortho4XP.

## How does X-Plane access scenery?

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

## How this project leverages this setup (high level description)

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


# Expert Usage and Overriding Defaults

## Warning
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

## Adding your own created sceneries

Ready to add your own sceneries? Great!

So as mentioned above, this tool effectively overrides the 'textures'
directory that XPlane is pointing to in order to location satellite imagery
that is referrenced by a scenery pack's terrain files.

Due to how XPlane identifies terrain information, these directories have been
split up into reasonable sized pieces, which is why each provided scenery pack
has numerous numbered directories. 

This project creates a special pass through filesystem that mounts directories into a location that XPlane can find and intercepts requests to '.dds' files.  This is handled through the magic of FUSE (Filesystem in UserSpacE).  FUSE is a common and standard feature of Linux, but requires extra stuff for other Operatings Systems.s

Sceneries stripped of satellite imagery, likely still have
coastline PNG files that must be preserved.  These are simply passed through when requested.

You can take advantage of this setup for your own scenery that you have
packaged:
* Place your scenery directory in `Custom Scenery/zAutoOrtho/scenery`

When execute Autoortho will detect directories in that scenery dir and mount these in your configured `Custom Scenery` directory.

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

