#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include "aoimage.h"

int main(void) {
    setvbuf(stderr, NULL, _IOLBF, BUFSIZ);
    setvbuf(stdout, NULL, _IOLBF, BUFSIZ);
    
    aoimage_t img;

    if(!aoimage_read_jpg("../testfiles/test_tile2.jpg", &img)) {
        printf("Error in loading the image\n");
        exit(1);
    }

    printf("Loaded image with a width of %dpx, a height of %dpx and %d channels\n", img.width, img.height, img.channels);

    aoimage_t img_2;
    aoimage_reduce_2(&img, &img_2);
    aoimage_dump("reduced", &img_2);
    aoimage_write_jpg("test_tile_2.jpg", &img_2, 90);

    aoimage_paste(&img, &img_2, 1024, 0);
    aoimage_write_jpg("test_tile_p.jpg", &img, 90);
}
