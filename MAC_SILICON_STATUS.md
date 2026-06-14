# AutoOrtho for Silicon Mac status

This branch contains experimental macOS Apple Silicon support using FUSE-T.

## Tested successfully

- Apple Silicon Mac
- X-Plane 12
- FUSE-T backend
- North America scenery region
- GUI launch flow
- Generic z_ao_* scenery mount discovery
- FUSE-T mount and symlink creation
- X-Plane process detection from configured X-Plane path
- Auto-stop/unmount after X-Plane quits
- Portable Python beta package with local wheelhouse/runtime creation

## Current user workflow

1. Install FUSE-T separately.
2. Launch the AutoOrtho GUI.
3. Set the X-Plane install directory.
4. Install at least one scenery region from the Scenery tab.
5. Click Run.
6. Launch X-Plane after the Terminal reports that mounts are ready.
7. Quit X-Plane when finished.
8. AutoOrtho stops and unmounts automatically when enabled.

## Key files

- autoortho/start_autoortho_mac_fuset.sh
- autoortho/mac_mount_fuset.py
- autoortho/config_ui.py
- autoortho/pydds.py
- autoortho/autoortho_fuse.py
- autoortho/aoimage/aoimage.dylib
- autoortho/lib/darwin_arm/libispc_texcomp.dylib
- autoortho/lib/darwin_arm/libstbdxt.dylib
- mac_package/build_mac_beta_package.sh
- mac_package/Start Auto Ortho for Silicon Mac.command
- mac_package/self_test_mac_beta_package.sh

## Known limitations

- X-Plane 12 has been tested; X-Plane 11 has not yet been validated.
- FUSE-T must be installed separately.
- The beta package is unsigned.
- A Terminal window remains visible for debugging.
- The current GUI polish is experimental.
- Multi-region mounting is supported by scanning installed z_ao_* folders, but only tested regions should be considered validated.

## Build beta package

From the repository root:

    ./mac_package/build_mac_beta_package.sh

The script creates:

    ~/Desktop/AutoOrtho-Silicon-Mac-Beta.zip

## Test beta package

Unzip the package, then run:

    ./self_test_mac_beta_package.sh
    ./"Start Auto Ortho for Silicon Mac.command"

## FUSE-T

This branch uses FUSE-T as the preferred macOS backend to avoid requiring macFUSE kernel-extension approval.
