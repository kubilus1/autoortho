ZIP?=zip
VERSION?=0.0.0

autoortho.pyz:
	mkdir -p build/autoortho
	cp -r autoortho/* build/autoortho/.
	python3 -m pip install -U -r ./build/autoortho/build-reqs.txt --target ./build/autoortho
	cd build && python3 -m zipapp -p "/usr/bin/env python3" autoortho

lin_bin: autoortho_lin_$(VERSION).bin
autoortho_lin_$(VERSION).bin: autoortho/*.py
	docker run --rm -v `pwd`:/code ubuntu:jammy /bin/bash -c "cd /code; ./buildreqs.sh; time make bin VERSION=$(VERSION)"
	mv autoortho_lin.bin $@

enter:
	docker run --rm -it -v `pwd`:/code ubuntu:focal /bin/bash

autoortho/.version:
	echo "$(VERSION)" > $@

bin: autoortho/.version
	python3 -m nuitka --verbose --verbose-output=nuitka.log \
		--linux-icon=autoortho/imgs/ao-icon.ico \
		--enable-plugin=tk-inter \
		--enable-plugin=eventlet \
		--include-data-file=./autoortho/.version*=. \
		--include-data-file=./autoortho/templates/*.html=templates/ \
		--include-data-file=./autoortho/lib/linux/*.so=lib/linux/ \
		--include-data-file=./autoortho/aoimage/*.so=aoimage/ \
		--include-data-dir=./autoortho/imgs=imgs \
		--onefile \
		./autoortho/__main__.py -o autoortho_lin.bin

_autoortho_win.exe: autoortho/.version
	python3 -m nuitka --verbose --verbose-output=nuitka.log \
		--mingw64 \
		--disable-ccache \
		--enable-plugin=tk-inter \
		--enable-plugin=eventlet \
		--windows-icon-from-ico=autoortho/imgs/ao-icon.ico \
		--assume-yes-for-downloads \
		--include-data-file=./autoortho/.version*=./ \
		--include-data-file=./autoortho/templates/*.html=templates/ \
		--include-data-file=./autoortho/lib/windows/*=lib/windows/ \
		--include-data-file=./autoortho/aoimage/*.dll=aoimage/ \
		--include-data-dir=./autoortho/imgs=imgs \
		--onefile \
		--disable-console \
		./autoortho/__main__.py -o autoortho_win.exe

__main__.dist: autoortho/.version
	python3 -m nuitka --verbose --verbose-output=nuitka.log \
		--mingw64 \
		--disable-ccache \
		--enable-plugin=tk-inter \
		--enable-plugin=eventlet \
		--windows-icon-from-ico=autoortho/imgs/ao-icon.ico \
		--assume-yes-for-downloads \
		--include-data-file=./autoortho/.version*=./ \
		--include-data-file=./autoortho/templates/*.html=templates/ \
		--include-data-file=./autoortho/lib/windows/*=lib/windows/ \
		--include-data-file=./autoortho/aoimage/*.dll=aoimage/ \
		--include-data-dir=./autoortho/imgs=imgs \
		--standalone \
		--disable-console \
		./autoortho/__main__.py -o autoortho_win.exe

win_exe: AutoOrtho_win_$(VERSION).exe
AutoOrtho_win_$(VERSION).exe: __main__.dist
	cp autoortho/imgs/ao-icon.ico .
	makensis -DPRODUCT_VERSION=$(VERSION) installer.nsi
	mv AutoOrtho.exe $@

win_zip: autoortho_win_$(VERSION).zip
autoortho_win_$(VERSION).zip: __main__.dist
	mv __main__.dist autoortho_release
	$(ZIP) $@ autoortho_release

testperf:
	python3.10 -m nuitka --verbose --verbose-output=nuitka.log  --include-data-dir=./autoortho/lib=lib --include-data-dir=./autoortho/testfiles=testfiles --onefile ./autoortho/perftest.py

%.txt: %.in
	pip-compile $<

serve_docs:
	docker run -p 8000:8000 -v `pwd`:/docs squidfunk/mkdocs-material

clean:
	-rm -rf build
	-rm -rf __main__.dist
	-rm -rf __main__.build
	
