#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <assert.h>
#include <string.h>
#include <errno.h>
#include <turbojpeg.h>

#include "aoimage.h"

#define TRUE 1
#define FALSE 0

AOIAPI void aoimage_delete(aoimage_t *img) {
    if (img->ptr)
        free(img->ptr);
    memset(img, 0, sizeof(aoimage_t));
}

// create empty rgba image
AOIAPI int32_t aoimage_create(aoimage_t *img, uint32_t width, uint32_t height, uint32_t r, uint32_t g, uint32_t b) {
    memset(img, 0, sizeof(aoimage_t));

    assert(height >=4 && (height & 3) == 0);    // multiple of 4
    int len = width * height * 4;
    img->ptr = malloc(len);
    if (NULL == img->ptr) {
        sprintf(img->errmsg, "can't malloc %d bytes", len);
        return FALSE;
    }

    img->width = width;
    img->height = height;
    img->channels = 4;
    img->stride = width * 4;

    uint32_t pixel = 0xff000000 | (r & 0xff) | (g & 0xff) << 8 | (b & 0xff) << 16;

    if (pixel == 0xff000000) {
        // if pixel color is 0 alpha does not matter here so we zero out everything
        memset(img->ptr, 0, len);
    } else {
        // fill row 0 with integer arithmetics
        uint32_t *uiptr = (uint32_t *)img->ptr;
        while (uiptr < (uint32_t *)(img->ptr + img->stride))
            *uiptr++ = pixel;

        uint8_t *uptr = img->ptr + img->stride;
        memcpy(uptr, img->ptr, img->stride);        // copy row 1 from 0
        uptr += img->stride;

        memcpy(uptr, img->ptr, 2 * img->stride);    // copy 2 + 3 from 0 + 1
        uptr += 2 *img->stride;

        while (uptr < img->ptr + len) {             // fill rest from 0-4
            memcpy(uptr, img->ptr, 4 * img->stride);
            uptr += 4 * img->stride;
        }

        assert(uptr == img->ptr + len);
    }

    return TRUE;
}

// dump header for debugging
AOIAPI void aoimage_dump(const char *title, const aoimage_t *img) {
    fprintf(stderr, "%s:\n\tptr:\t\%p\n\twidth:\t%d\n\theight\t%d\n\tstride\t%d\n\tchans:\t%d\n",
            title, img->ptr, img->width, img->height, img->stride, img->channels);
    //fflush(stderr);
}

// no longer really needed as jpeg-turbo already returns RGBA
AOIAPI int32_t aoimage_2_rgba(const aoimage_t *s_img, aoimage_t *d_img) {
    // already 4 channels means copy
    if (4 == s_img->channels) {
        memcpy(d_img, s_img, sizeof(aoimage_t));
        int dlen = s_img->width * s_img->height * 4;
        d_img->ptr = malloc(dlen);
        if (NULL == d_img->ptr) {
            sprintf(d_img->errmsg, "can't malloc %d bytes", dlen);
            return FALSE;
        }
        memcpy(d_img->ptr, s_img->ptr, dlen);
        return TRUE;
    }

    assert(s_img->channels == 3);

    int slen = s_img->width * s_img->height * 3;
    int dlen = s_img->width * s_img->height * 4;
    uint8_t *dest = malloc(dlen);
    if (NULL == dest) {
		sprintf(d_img->errmsg, "can't malloc %d bytes", dlen);
        d_img->ptr = NULL;
        return FALSE;
    }

    const uint8_t *sptr = s_img->ptr;
    const uint8_t *send = sptr + slen;
    uint8_t *dptr = dest;
    while (sptr < send) {
        *dptr++ = *sptr++;
        *dptr++ = *sptr++;
        *dptr++ = *sptr++;
        *dptr++ = 0xff;
        //*dptr++ = 0x00;
    }

   d_img->ptr = dest;
   d_img->width = s_img->width;
   d_img->height = s_img->height;
   d_img->stride = 4 * d_img->width;
   d_img->channels = 4;
   return TRUE;
}

AOIAPI int32_t aoimage_read_jpg(const char *filename, aoimage_t *img) {
	long in_jpg_size;
	unsigned char *in_jpg_buff;

    FILE *fd = fopen(filename, "rb");
    if (fd == NULL) {
        strncpy(img->errmsg, strerror(errno), sizeof(img->errmsg)-1);
		return FALSE;
	}

    if (fseek(fd, 0, SEEK_END) < 0 || ((in_jpg_size = ftell(fd)) < 0) ||
            fseek(fd, 0, SEEK_SET) < 0) {
        strcpy(img->errmsg, "error determining input file size");
        return FALSE;
    }

    if (in_jpg_size == 0) {
        strcpy(img->errmsg, "inputfile has no data");
        return FALSE;
    }

    //fprintf(stderr, "File size %ld\n", in_jpg_size);
	in_jpg_buff = malloc(in_jpg_size);
    if (in_jpg_buff == NULL) {
		sprintf(img->errmsg, "can't malloc %ld bytes", in_jpg_size);
		return FALSE;
	}

    int rc = fread(in_jpg_buff, 1, in_jpg_size, fd);
    if (rc < 0) {
        strncpy(img->errmsg, strerror(errno), sizeof(img->errmsg)-1);
        return FALSE;
    }

    //fprintf(stderr, "Input: Read %d/%lu bytes\n", rc, in_jpg_size);
    fclose(fd);
    int res = aoimage_from_memory(img, in_jpg_buff, in_jpg_size);
    free(in_jpg_buff);
    return res;
}
AOIAPI int32_t aoimage_write_jpg(const char *filename, aoimage_t *img, int32_t quality) {
    tjhandle tjh = NULL;
    unsigned char *out_jpg_buf = NULL;
    unsigned long out_jpg_size = 0;
    FILE *fd = NULL;

    int result = FALSE;

    tjh = tjInitCompress();
    if (NULL == tjh) {
        strcpy(img->errmsg, "Can't allocate tjInitCompress");
        goto err;
    }

    int rc = tjCompress2(tjh, img->ptr, img->width, 0, img->height, TJPF_RGBA,
                         &out_jpg_buf, &out_jpg_size, TJSAMP_444, quality, 0);
    if (rc) {
        strncpy(img->errmsg, tjGetErrorStr2(tjh), sizeof(img->errmsg) - 1);
        goto err;
    }

    //fprintf(stderr, "jpg_size: %ld\n", out_jpg_size);
    fd = fopen(filename, "wb");
    if (fd == NULL) {
        strncpy(img->errmsg, strerror(errno), sizeof(img->errmsg)-1);
		goto err;
	}

    if (fwrite(out_jpg_buf, 1, out_jpg_size, fd) < 0) {
        strncpy(img->errmsg, strerror(errno), sizeof(img->errmsg)-1);
        goto err;
    }

    result = TRUE;

   err:
    if (fd) fclose(fd);
    if (tjh) tjDestroy(tjh);
    if (out_jpg_buf) tjFree(out_jpg_buf);
    return result;
}

AOIAPI int32_t aoimage_reduce_2(const aoimage_t *s_img, aoimage_t *d_img) {
    if (s_img->channels != 4) {
		sprintf(d_img->errmsg, "channel error %d != 4", s_img->channels);
        d_img->ptr = NULL;
        return FALSE;
    }

    if ( (s_img->width < 4)
           || (s_img->width != s_img->height)
           || (0 != (s_img->width & 0x03)) ) {
		sprintf(d_img->errmsg, "width error: %d", s_img->width);
        d_img->ptr = NULL;
        return FALSE;
    }

    //aoimage_dump("aoimage_reduce_2 s_img", s_img);

    int slen = s_img->width * s_img->height * 4;
    int dlen = slen / 4;
    uint8_t *dest = malloc(dlen);
    if (NULL == dest) {
		sprintf(d_img->errmsg, "can't malloc %d bytes", dlen);
        d_img->ptr = NULL;
        return FALSE;
    }

    const uint8_t *srptr = s_img->ptr;      // source row start
    const uint8_t *send = srptr + slen;
    uint8_t *dptr = dest;
    int stride = s_img->width * 4;

    // fprintf(stderr, "%p %d %d %d\n", sptr, slen, dlen, stride); fflush(stderr);
    while (srptr < send) {
        const uint8_t *sptr = srptr;
        while (sptr < srptr + stride) {
            uint8_t r = (sptr[0] + sptr[4] + sptr[stride] + sptr[stride + 4]) / 4;
            sptr++;
            uint8_t g = (sptr[0] + sptr[4] + sptr[stride] + sptr[stride + 4]) / 4;
            sptr++;
            uint8_t b = (sptr[0] + sptr[4] + sptr[stride] + sptr[stride + 4]) / 4;
            sptr += 1 + 1 + 4;  // skip over alpha + next RGBA

            *dptr++ = r;
            *dptr++ = g;
            *dptr++ = b;
            *dptr++ = 0xff;
            //*dptr++ = 0x00;
            assert(dptr <= dest + dlen);
        }
        srptr += 2* stride;
    }
    d_img->ptr = dest;
    d_img->width = s_img->width / 2;
    d_img->height = s_img->height / 2;
    d_img->stride = 4 * d_img->width;
    d_img->channels = 4;

    assert(dptr == dest + dlen);
    assert(dlen == d_img->width * d_img->height * 4);
    return TRUE;
}

AOIAPI int32_t aoimage_scale(const aoimage_t *s_img, aoimage_t *d_img, uint32_t factor) {
    assert(s_img->channels == 4);

    assert((s_img->width >= 4)
           && (s_img->width == s_img->height)
           && (0 == (s_img->width & 0x03)));

    uint32_t slen = s_img->width * s_img->height;
    uint32_t dlen = slen * 16 * factor;
   
    //fprintf(stderr, "malloc(%d)\n", (dlen*4)); fflush(stderr); 
    uint32_t *dest = malloc(dlen*4);
    if (NULL == dest) {
		sprintf(d_img->errmsg, "can't malloc %d bytes", dlen);
        d_img->ptr = NULL;
        return FALSE;
    }

    //const uint8_t *srptr = s_img->ptr;      // source row start
    //const uint8_t *send = srptr + slen;
   
    // Start destination image pointer at the start 
    uint32_t *dptr = dest;

    // Length of one row of the source image
    int d_stride = s_img->width * factor;
    //fprintf(stderr, "%d %d %d\n", slen, dlen, d_stride); fflush(stderr);
    int s_stride = s_img->width;
    //fprintf(stderr, "%p %d %d %d\n", srptr, slen, dlen, d_stride); fflush(stderr);

    const uint32_t *sptr = s_img->ptr;
    
    int d_idx;
    int s_col_count = 0;

    // Iterate over source image
    for (int i=0; i<slen; i++) {
        
        s_col_count++;

        // Grab 32 bits
        uint32_t s_rgba = sptr[i];
        for (int j=0; j<factor; j++) {
            //col
            for (int k=0; k<factor; k++) {
                //row
                d_idx = ((d_stride * k) + j);
                //fprintf(stderr, "D_IDX: %d D_STRIDE: %d k: %d  j: %d    %d  %d \n", d_idx, d_stride, k, j, (d_stride * k), (d_stride * k) + j); fflush(stderr);
                dptr[d_idx] = s_rgba;
            }
        }
        
        dptr += factor;

        if (s_col_count == s_stride) {
            dptr += d_stride * (factor - 1);
            s_col_count = 0;
            //fprintf(stderr, "STARTROW %d %p %p\n", i, sptr, dptr); fflush(stderr);
        } 

    }

    d_img->ptr = dest;
    d_img->width = s_img->width * factor;
    d_img->height = s_img->height * factor;
    d_img->stride = 4 * d_img->width;
    d_img->channels = 4;

    //fprintf(stderr, "start: %p end: %p  expected: %p len: %d diff: %d \n", dest, dptr, (dest + dlen), dlen, (dest+dlen) - dptr); fflush(stderr);
    //assert(dptr == (dest + dlen));
    //fprintf(stderr, "width: %d height: %d \n", d_img->width, d_img->height); fflush(stderr);
    //assert((s_img->width * s_img->height * 4) << factor == d_img->width * d_img->height * 4);
    return TRUE;
}

AOIAPI int32_t aoimage_from_memory(aoimage_t *img, const uint8_t *data, uint32_t len) {
    memset(img, 0, sizeof(aoimage_t));

    // strange enough tj does not check the signture */
    uint32_t signature = *(uint32_t *)data & 0x00ffffff;

    if (signature != 0x00ffd8ff) {
        strcpy(img->errmsg, "data is not a JPEG");
        return FALSE;
    }

    tjhandle tjh = NULL;
    unsigned char *img_buff = NULL;

    tjh = tjInitDecompress();
    if (NULL == tjh) {
        strcpy(img->errmsg, "Can't allocate tjInitDecompress");
        goto err;
    }

    int subsamp, width, height, color_space;

    if (tjDecompressHeader3(tjh, data, len, &width, &height, &subsamp, &color_space) < 0) {
        strncpy(img->errmsg, tjGetErrorStr2(tjh), sizeof(img->errmsg) - 1);
        goto err;
    }

    //fprintf(stderr, "%d %d %d\n", width, height, subsamp); fflush(stderr);

    unsigned long img_size = width * height * tjPixelSize[TJPF_RGBA];
    //fprintf(stderr, "img_size %ld bytes\n", img_size);
    img_buff = malloc(img_size);
    if (img_buff == NULL) {
		sprintf(img->errmsg, "can't malloc %ld bytes", img_size);
		goto err;
	}

    //printf("Pixel format: %d\n", TJPF_RGBA);

    if (tjDecompress2(tjh, data, len, img_buff, width, 0, height, TJPF_RGBA, TJFLAG_FASTDCT) < 0) {
        strncpy(img->errmsg, tjGetErrorStr2(tjh), sizeof(img->errmsg) - 1);
        goto err;
    }

    tjDestroy(tjh);

    img->ptr = img_buff;
    img->width = width;
    img->height = height;
    img->channels = 4;
    img->stride = img->channels * img->width;
    return TRUE;

err:
    if (tjh) tjDestroy(tjh);
    if (img_buff) free(img_buff);
    return FALSE;
}

AOIAPI void aoimage_tobytes(aoimage_t *img, uint8_t *data) {
    memcpy(data, img->ptr, img->width * img->height * img->channels);
}

AOIAPI int32_t aoimage_copy(const aoimage_t *s_img, aoimage_t *d_img, uint32_t s_height_only) {
    assert(NULL != s_img->ptr);
    assert(s_height_only <= s_img->height);

    if (0 == s_height_only)
        s_height_only = s_img->height;

    int dlen = s_img->width * s_height_only * s_img->channels;
    uint8_t *dest = malloc(dlen);
    if (NULL == dest) {
		sprintf(d_img->errmsg, "can't malloc %d bytes", dlen);
        d_img->ptr = NULL;
        return FALSE;
    }

    memcpy(dest, s_img->ptr, dlen);
    d_img->ptr = dest;
    d_img->width = s_img->width;
    d_img->height = s_height_only;
    d_img->stride = 4 * d_img->width;
    d_img->channels = 4;
    d_img->errmsg[0] = '\0';
    return TRUE;

}

AOIAPI int32_t aoimage_paste(aoimage_t *img, const aoimage_t *p_img, uint32_t x, uint32_t y) {
    assert(x + p_img->width <= img->width);
    assert(y + p_img->height <= img->height);
    assert((img->channels == 4) && (p_img->channels == 4));

    //aoimage_dump("paste img", img);
    //aoimage_dump("paste P", p_img);
    //fprintf(stderr, "aoimage_paste: %d %d\n", x, y);

    uint8_t *ip = img->ptr + (y * img->width * 4) + x * 4;  // lower left corner of image
    uint8_t *pp = p_img->ptr;

    for (int i = 0; i < p_img->height; i++) {
        memcpy(ip, pp, p_img->width * 4);
        ip += img->width * 4;
        pp += p_img->width * 4;
    }

    return TRUE;
}

AOIAPI int32_t aoimage_crop(aoimage_t *img, const aoimage_t *c_img, uint32_t x, uint32_t y) {
    assert(x + c_img->width <= img->width);
    assert(y + c_img->height <= img->height);
    assert((img->channels == 4) && (c_img->channels == 4));

    uint8_t *ip = img->ptr + (y * img->width * 4) + x * 4;  // lower left corner of image
    uint8_t *cp = c_img->ptr;

    for (int i = 0; i < c_img->height; i++) {
        memcpy(cp, ip, c_img->width * 4);
        ip += img->width * 4;
        cp += c_img->width * 4;
    }

    return TRUE;
}

AOIAPI int32_t aoimage_desaturate(aoimage_t *img, float saturation) {
    assert(img->channels == 4);

    int len = img->width * img->height * 4;
    for (uint8_t *ptr = img->ptr; ptr < img->ptr + len; ptr += 4) {
        float luma = 0.212671f * ptr[0] + 0.715160f * ptr[1] + 0.072169f * ptr[2];
        float x = (1.0f - saturation) * luma;
        ptr[0] = (uint8_t)(saturation * ptr[0] + x);
        ptr[1] = (uint8_t)(saturation * ptr[1] + x);
        ptr[2] = (uint8_t)(saturation * ptr[2] + x);
    }

    return TRUE;
}

