# AutoOrtho - Automatic orthophotos for X-Plane 11& 12

Orthophoto satellite imagery is something that has been supported by X-Plane
for some time.  However, this requires a large commitment of storage
space and patience since high-resolution imagery would need to be downloaded and prepared
ahead of time.

This project provides a way to retrieve only the satellite imagery you need as you fly,
wherever you choose to in the world!

[![Video](https://img.youtube.com/vi/seuguds8GX0/hqdefault.jpg)](https://www.youtube.com/watch?v=seuguds8GX0)

## Current Version Software Characteristics
* Does not remove cached high-res downloaded image automatically, these files can get very large(>100GB) overtime and require manual intervention to delete.  They are stored in the configured `paths.cache_dir` (see `.autoortho` configuration file) directory.
  * Hence, if you fly through the same place without deleting you cache, the previously cached file will be accessed again without any downloads
* Unfinished downloads are store in (C:\Users\username\.autoortho-data/downloads) folder by default
* The console output log is stored in (C:\Users\username\.autoortho-data/)
* The configuration file, (.autoortho) is stored as a independent file in (C:\Users\username\.autoortho-data)

## Links for more information on
* Documentation & Steps to Install: (https://kubilus1.github.io/autoortho/)
* FAQ: (https://kubilus1.github.io/autoortho/faq/)
* Discussions and help: (https://github.com/kubilus1/autoortho/discussions)
* Latest release: (https://github.com/kubilus1/autoortho/releases/latest)
* X-plane.org: (https://github.com/kubilus1/autoortho)

# As seen in
[Swiss001:X-Plane Now Has Worldwide Satellite Scenery STREAMING](https://www.youtube.com/watch?v=qTbBCW2xZRg&t=1sg)
