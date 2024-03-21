#ifndef _AOIMAGE_H_
#define _AOIMAGE_H_

#include <stdint.h>

#ifdef _WIN32

  /* You should define ADD_EXPORTS *only* when building the DLL. */
  #ifdef AOI_EXPORTS
    #define AOIAPI __declspec(dllexport)
  #else
    #define AOIAPI __declspec(dllimport)
  #endif

  /* Define calling convention in one place, for convenience. */
  #define AOICALL __cdecl

#else /* _WIN32 not defined. */

  /* Define with no value on non-Windows OSes. */
  #define AOIAPI __attribute__((__visibility__("default")))
  #define AOICALL

#endif
typedef struct
{
    uint8_t* ptr;
    int32_t width;
    int32_t height;
    int32_t stride;     // in bytes
    // up to here identical to rgba_surface
    int32_t channels;
    char errmsg[80];    // a possible error message
} aoimage_t;

// dump header for debugging
AOIAPI void aoimage_dump(const char *title, const aoimage_t *img);

// no longer really needed as jpeg-turbo already returns RGBA
AOIAPI int32_t aoimage_2_rgba(const aoimage_t *s_img, aoimage_t *d_img);

AOIAPI int32_t aoimage_read_jpg(const char *filename, aoimage_t *img);
AOIAPI int32_t aoimage_write_jpg(const char *filename, aoimage_t *img, int32_t quality);
AOIAPI int32_t aoimage_reduce_2(const aoimage_t *s_img, aoimage_t *d_img);
AOIAPI int32_t aoimage_scale(const aoimage_t *s_img, aoimage_t *d_img, uint32_t factor);
AOIAPI void aoimage_delete(aoimage_t *img);
AOIAPI int32_t aoimage_create(aoimage_t *img, uint32_t width, uint32_t height, uint32_t r, uint32_t g, uint32_t b);
AOIAPI int32_t aoimage_from_memory(aoimage_t *img, const uint8_t *data, uint32_t len);
AOIAPI void aoimage_tobytes(aoimage_t *img, uint8_t *data);
AOIAPI int32_t aoimage_copy(const aoimage_t *s_img, aoimage_t *d_img, uint32_t s_height_only);

// in place: img + pasted(p_img)
AOIAPI int32_t aoimage_paste(aoimage_t *img, const aoimage_t *p_img, uint32_t x, uint32_t y);
AOIAPI int32_t aoimage_crop(aoimage_t *img, const aoimage_t *c_img, uint32_t x, uint32_t y);

// in place desaturation
AOIAPI int32_t aoimage_desaturate(aoimage_t *img, float saturation);
#endif
