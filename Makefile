ZIP?=zip

autoortho.pyz:
	mkdir -p build/autoortho
	cp -r autoortho/* build/autoortho/.
	python3 -m pip install -U -r ./build/autoortho/build-reqs.txt --target ./build/autoortho
	cd build && python3 -m zipapp -p "/usr/bin/env python3" autoortho

autoortho_lin.bin: autoortho/*.py
	docker run --rm -v `pwd`:/code ubuntu:focal /bin/bash -c "cd /code; ./buildreqs.sh; time make bin"

enter:
	docker run --rm -it -v `pwd`:/code ubuntu:focal /bin/bash

bin:
	python3.10 -m nuitka --verbose --verbose-output=nuitka.log \
		--linux-icon=autoortho/imgs/ao-icon.ico \
		--enable-plugin=tk-inter \
		--enable-plugin=eventlet \
		--include-data-file=./autoortho/templates/*.html=templates/ \
		--include-data-file=./autoortho/lib/linux/*.so=lib/linux/ \
		--include-data-file=./autoortho/aoimage/*.so=aoimage/ \
		--include-data-dir=./autoortho/imgs=imgs \
		--onefile \
		./autoortho/__main__.py -o autoortho_lin.bin

autoortho_osx.bin:
	python3.10 -m nuitka --verbose --verbose-output=nuitka.log \
		--macos-app-icon=autoortho/imgs/ao-icon.ico \
		--enable-plugin=eventlet \
		--enable-plugin=tk-inter \
		--include-data-file=./autoortho/templates/*.html=templates/ \
		--include-data-file=./autoortho/lib/darwin_arm/*.dylib=lib/darwin_arm/ \
		--include-data-file=./autoortho/aoimage/*.dylib=aoimage/ \
		--include-data-dir=./autoortho/imgs=imgs \
		--onefile \
		./autoortho/__main__.py -o autoortho_osx.bin

autoortho_win.exe:
	python3 -m nuitka --verbose --verbose-output=nuitka.log \
		--mingw64 \
		--disable-ccache \
		--enable-plugin=tk-inter \
		--enable-plugin=eventlet \
		--windows-icon-from-ico=autoortho/imgs/ao-icon.ico \
		--assume-yes-for-downloads \
		--include-data-file=./autoortho/templates/*.html=templates/ \
		--include-data-file=./autoortho/lib/windows/*=lib/windows/ \
		--include-data-file=./autoortho/aoimage/*.dll=aoimage/ \
		--include-data-dir=./autoortho/imgs=imgs \
		--onefile \
		./autoortho/__main__.py -o autoortho_win.exe

__main__.dist:
	python3 -m nuitka --verbose --verbose-output=nuitka.log \
		--mingw64 \
		--disable-ccache \
		--enable-plugin=tk-inter \
		--enable-plugin=eventlet \
		--windows-icon-from-ico=autoortho/imgs/ao-icon.ico \
		--assume-yes-for-downloads \
		--include-data-file=./autoortho/templates/*.html=templates/ \
		--include-data-file=./autoortho/lib/windows/*=lib/windows/ \
		--include-data-file=./autoortho/aoimage/*.dll=aoimage/ \
		--include-data-dir=./autoortho/imgs=imgs \
		--standalone \
		./autoortho/__main__.py -o autoortho_win.exe
autoortho_win.zip: __main__.dist
	mv __main__.dist autoortho_release
	$(ZIP) $@ autoortho_release

testperf:
	python3.10 -m nuitka --verbose --verbose-output=nuitka.log  --include-data-dir=./autoortho/lib=lib --include-data-dir=./autoortho/testfiles=testfiles --onefile ./autoortho/perftest.py

%.txt: %.in
	pip-compile $<

clean:
	rm -rf build
