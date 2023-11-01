#!/bin/sh
# Installs required environment for OSX

# Check this is run on a Mac
if [[ ! $OSTYPE == 'darwin'* ]]; then
  echo "buildreqs_osx.sh: This script is for OSX (Mac) only.";
  exit 1;
fi

if [[ $(sysctl -n machdep.cpu.brand_string) =~ "Apple" ]]; then
  CPU_ARCH="Apple";
else  
  CPU_ARCH="Intel";
fi;

echo "Configuring build environment for Macintosh with an $CPU_ARCH CPU."

# First make sure homebrew is installed
# and updated

#if [[ $(command -v brew) == "" ]]; then
#    # Prompt for installation
#    while true; do
#        read -p "Homebrew not installed. Install [y/n]? " yn
#        case $yn in
#            [yY] ) echo "Installing Homebrew...";
#                break;;
#            [nN] ) echo "Exiting...";
#                exit;;
#            * ) echo "Invalid choice ($yn).";;
#        esac
#    done    
#    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
#else
#    echo "Updating Homebrew"
#    brew update
#fi

# Install brew packages needed
# Currently no brew packages needed

# Make sure Miniforge3 or is installed
if [[ $(command -v conda) == "" ]]; then
    # Prompt for installation
    while true; do
        read -p "Miniforge3 not installed. Install [y/n]? " yn
        case $yn in
            [yY] ) echo "OK, preparing to download Miniforge3...";
                if [[ $CPU_ARCH=="Apple" ]]; then
                  MF_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh";
                else
                  MF_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh";
                fi;
                break;;
            [nN] ) echo "Exiting...";
                exit;;
            * ) echo "Invalid choice ($yn).";;
        esac
    done    
    curl -LJ0 "$MF_URL" --output mf3_installer.sh;
    echo "Downloaded mf3_installer.sh. Starting installer..."
    echo bash mf3_installer.sh
    echo "Removing Miniforge3 installer"
    rm mf3_installer.sh
    echo "Miniforge3 install complete."
    echo "\nClose terminal window, start a new terminal window and re-run buildreqs.sh to continue."
    exit 0
fi

# Activate
echo "Creating Miniforge3 or Conda environment autoortho..."
conda env create -f conda_autoortho.yml

echo "Activating autoortho environment"
conda activate autoortho

# Installing modules not available from conda-forge
echo "Installing python package refuse..."
pip install refuse

echo 'System setup for Macintosh is complete.\n\nTo compile:\ns1. conda activate autoortho.\n2. make osx_bin\n'
echo 'To run without compiling:\n1. conda activate autoortho\n2. python3 autoortho/'

