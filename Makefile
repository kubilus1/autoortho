autoortho.pyz:
	mkdir -p build/autoortho
	cp autoortho/* build/autoortho/.
	python3 -m pip install -U -r build/autoroth/build-reqs.txt --target build/autoortho
	cd build && python3 -m zipapp -p "/usr/bin/env python3" autoortho

clean:
	rm -rf build
