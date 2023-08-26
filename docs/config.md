# Configuration

Setup and configuration for most use cases should be pretty simple. The important settings are:

* Scenery install path
* X-Plane install path
* Downloader directory

## Scenery install path
This is the location that scenery will be installed to.  Previously this defaulted to a user's existing X-Plane Custom Scenery directory, but that is no longer the case.  

It should be possible to set this to a convenient location with enough room to install scenery packages.  Each scenery package can take around 20-30GB.

This can be an external NAS or separate drive, but I have not tried all drive combinations.  Speed of external storage will naturally impact performance to a certain degree.  Plan accordingly.

## X-Plane install path
This is the X-Plane install location.  Under this directory should be X-Plane's `Custom Scenery` directory. 
*IT IS IMPORTANT THIS IS THE CORRECT LOCATION*

From this directory AutoOrtho will create mount points and run the program.

*IF THIS IS NOT CORRECT THINGS WILL NOT WORK RIGHT*

## Download directory
This is the path that will be used to temporarily store zip files and other fetched files for scenery setup.  By default this will be in under the user's home dir under `.autoortho-data/downloads`

For Windows users, it is highly recommended to set a Windows Defender exception to this directory otherwise expect *VERY* slow setup of scenery.

This folder can be set to any convenient location with enough space for scenery downloads (20-30GB per).

## User config file location

The configuration file `.autoortho` is located in the user's home directory.  

