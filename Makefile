autoortho.pyz:
	mkdir -p build/autoortho
	cp -r autoortho/* build/autoortho/.
	python3 -m pip install -U -r ./build/autoortho/build-reqs.txt --target ./build/autoortho
	cd build && python3 -m zipapp -p "/usr/bin/env python3" autoortho

autoortho.bin: autoortho/*.py
	docker run -it --rm -v `pwd`:/code /bin/bash -c "cd /code; ./buildreqs.sh; time make bin"

bin:
	python3 -m nuitka --verbose --verbose-output=nuitka.log --enable-plugin=tk-inter --include-data-file=./autoortho/templates/*.html=templates/ --include-data-dir=./autoortho/lib=lib --include-data-dir=./autoortho/imgs=imgs --onefile ./autoortho/autoortho.py

exe:
	py -m nuitka --verbose --verbose-output=nuitka.log --enable-plugin=tk-inter --assume-yes-for-downloads --include-data-file=./autoortho/templates/*.html=templates/ --include-data-file=./autoortho/lib/windows/*=lib/windows/ --include-data-dir=./autoortho/imgs=imgs --onefile ./autoortho/autoortho.py

testperf:
	python3.10 -m nuitka --verbose --verbose-output=nuitka.log  --include-data-dir=./autoortho/lib=lib --include-data-dir=./autoortho/testfiles=testfiles --onefile ./autoortho/perftest.py

%.txt: %.in
	pip-compile $<

clean:
	rm -rf build
