/* SPDX-License-Identifier: GPL-3.0-only */
/* SAGGA HUB PC port: a USB-MIDI device with two cables ("SAGGA HUB 1", "SAGGA HUB 2") */
#include <string.h>
#include "tusb.h"
#include "pico/unique_id.h"

#define USB_VID 0x1209u                   /* pid.codes */
#define USB_PID 0x7A02u                   /* (0x7A01 is the Brick link): a test PID; ask pid.codes before selling anything */

static const tusb_desc_device_t desc_device = {
    .bLength = sizeof(tusb_desc_device_t), .bDescriptorType = TUSB_DESC_DEVICE, .bcdUSB = 0x0200,
    .bDeviceClass = 0x00, .bDeviceSubClass = 0x00, .bDeviceProtocol = 0x00, .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = USB_VID, .idProduct = USB_PID, .bcdDevice = 0x0010,
    .iManufacturer = 1, .iProduct = 2, .iSerialNumber = 3, .bNumConfigurations = 1};

const uint8_t *tud_descriptor_device_cb(void) { return (const uint8_t *)&desc_device; }

enum { ITF_NUM_MIDI = 0, ITF_NUM_MIDI_STREAMING, ITF_NUM_TOTAL };
#define EPNUM_MIDI_OUT 0x01
#define EPNUM_MIDI_IN 0x81
#define NUM_CABLES 2
#define CONFIG_TOTAL_LEN (TUD_CONFIG_DESC_LEN + TUD_MIDI_DESC_HEAD_LEN + TUD_MIDI_DESC_JACK_LEN * NUM_CABLES + TUD_MIDI_DESC_EP_LEN(NUM_CABLES) * 2)

static const uint8_t desc_configuration[] = {
    TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, CONFIG_TOTAL_LEN, 0x00, 100),
    TUD_MIDI_DESC_HEAD(ITF_NUM_MIDI, 0, NUM_CABLES),
    TUD_MIDI_DESC_JACK_DESC(1, 4),                                 /* cable 1: string 4 "SAGGA HUB 1" */
    TUD_MIDI_DESC_JACK_DESC(2, 5),                                 /* cable 2: string 5 "SAGGA HUB 2" */
    TUD_MIDI_DESC_EP(EPNUM_MIDI_OUT, 64, NUM_CABLES), TUD_MIDI_JACKID_IN_EMB(1), TUD_MIDI_JACKID_IN_EMB(2),
    TUD_MIDI_DESC_EP(EPNUM_MIDI_IN, 64, NUM_CABLES), TUD_MIDI_JACKID_OUT_EMB(1), TUD_MIDI_JACKID_OUT_EMB(2),
};

const uint8_t *tud_descriptor_configuration_cb(uint8_t index) { (void)index; return desc_configuration; }

static const char *const string_desc[] = {
    (const char[]){0x09, 0x04},           /* 0: English */
    "SAGGA",                              /* 1: manufacturer */
    "SAGGA HUB",                          /* 2: product */
    NULL,                                 /* 3: the serial, from the flash id */
    "SAGGA HUB 1",                        /* 4 */
    "SAGGA HUB 2",                        /* 5 */
};

static uint16_t desc_str[32];

const uint16_t *tud_descriptor_string_cb(uint8_t index, uint16_t langid)
{
    (void)langid;
    uint8_t n;
    if (index == 0) { memcpy(&desc_str[1], string_desc[0], 2); n = 1; }
    else {
        char serial[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];
        const char *s;
        if (index >= sizeof string_desc / sizeof string_desc[0]) return NULL;
        if (index == 3) { pico_get_unique_board_id_string(serial, sizeof serial); s = serial; }
        else s = string_desc[index];
        n = (uint8_t)strlen(s);
        if (n > 31) n = 31;
        for (uint8_t i = 0; i < n; i++) desc_str[1 + i] = s[i];
    }
    desc_str[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * n + 2));
    return desc_str;
}
