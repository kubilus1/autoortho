Building universal libstbd
git clone https://github.com/nothings/stb.git

create stb_dxt.c with
#include "stb_dxt.h"
#define STB_DXT_IMPLEMENTATION

build dynlib with
clang -arch x86_64 -arch arm64 -c stb_dxt.c
clang -o libstbdxt.dylib -shared -rdynamic -nodefaultlibs -arch arm64 -arch x86_64 stb_dxt.o

