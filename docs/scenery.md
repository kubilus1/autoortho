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


