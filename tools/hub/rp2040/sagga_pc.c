/* SPDX-License-Identifier: GPL-3.0-only */
/* SAGGA HUB PC port, the RP2040 side (a Waveshare RP2040-Zero on the hub's "PC" USB-C socket).
 *
 * To the computer it is a class-compliant USB-MIDI interface with two ports, "SAGGA HUB 1" and "SAGGA HUB 2".
 * To the Pi it is a UART (GP0 TX, GP1 RX, 1,000,000 baud, 8N1) carrying the same USB-MIDI 4-byte packets as SLIP
 * frames, both ways (slip_midi.h; the Pi runs tools/hub/sagga_pc_host.py). The RP2040 does no MIDI itself: it
 * moves packets. The board's RGB LED (WS2812 on GP16) blinks with the traffic: green from the computer, blue
 * from the Pi, red when the UART overflows.
 *
 * Build (Pico SDK 1.5 or 2.x): see README.md. Board: waveshare_rp2040_zero. */
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/gpio.h"
#include "hardware/irq.h"
#include "hardware/sync.h"
#include "tusb.h"
#include "slip_midi.h"

#define UART_ID uart0
#define UART_BAUD 1000000
#define UART_TX_PIN 0
#define UART_RX_PIN 1
#define LED_PIN 16

/* ---- a ring for the UART receive interrupt */
#define RX_RING 1024u
static volatile uint8_t rx_ring[RX_RING];
static volatile uint32_t rx_head, rx_tail;
static volatile uint32_t rx_overflow;

static void on_uart_rx(void)
{
    while (uart_is_readable(UART_ID)) {
        uint8_t b = uart_getc(UART_ID);
        uint32_t next = (rx_head + 1u) % RX_RING;
        if (next == rx_tail) { rx_overflow++; continue; }
        rx_ring[rx_head] = b;
        rx_head = next;
    }
}

/* ---- the LED: a WS2812 bit-banged (one pixel, written rarely, interrupts off for 30 us) */
static void ws2812_put(uint8_t r, uint8_t g, uint8_t b)
{
    uint32_t grb = ((uint32_t)g << 16) | ((uint32_t)r << 8) | b, i;
    uint32_t save = save_and_disable_interrupts();
    for (i = 0; i < 24; i++) {
        if (grb & 0x800000u) { gpio_put(LED_PIN, 1); busy_wait_at_least_cycles(90); gpio_put(LED_PIN, 0); busy_wait_at_least_cycles(40); }
        else { gpio_put(LED_PIN, 1); busy_wait_at_least_cycles(40); gpio_put(LED_PIN, 0); busy_wait_at_least_cycles(90); }
        grb <<= 1;
    }
    restore_interrupts(save);
    busy_wait_us(60);
}

static uint32_t led_from_pc, led_from_pi, led_err;

static void led_task(void)
{
    static uint32_t last;
    uint32_t now = to_ms_since_boot(get_absolute_time());
    if (now - last < 40) return;
    last = now;
    ws2812_put(led_err ? 40 : 0, led_from_pc ? 30 : 0, led_from_pi ? 30 : 0);
    if (led_from_pc) led_from_pc--;
    if (led_from_pi) led_from_pi--;
    if (led_err) led_err--;
}

int main(void)
{
    uint8_t pkt[4], enc[10];
    slip_dec_t dec = {{0}, 0, 0};
    static uint32_t last_overflow;

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
    uart_init(UART_ID, UART_BAUD);
    gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);
    uart_set_hw_flow(UART_ID, false, false);
    uart_set_format(UART_ID, 8, 1, UART_PARITY_NONE);
    uart_set_fifo_enabled(UART_ID, true);
    irq_set_exclusive_handler(UART0_IRQ, on_uart_rx);
    irq_set_enabled(UART0_IRQ, true);
    uart_set_irq_enables(UART_ID, true, false);
    tusb_init();
    ws2812_put(0, 0, 0);

    for (;;) {
        tud_task();
        /* computer -> Pi: every packet the host sent, as a SLIP frame */
        while (tud_midi_available()) {
            if (!tud_midi_packet_read(pkt)) break;
            size_t n = slip_encode_pkt(pkt, enc);
            uart_write_blocking(UART_ID, enc, n);
            led_from_pc = 3;
        }
        /* Pi -> computer: the frames the UART received, as packets (the cable number is in the packet) */
        while (rx_tail != rx_head) {
            uint8_t b = rx_ring[rx_tail];
            rx_tail = (rx_tail + 1u) % RX_RING;
            if (slip_decode_byte(&dec, b, pkt)) {
                if (tud_midi_mounted()) tud_midi_packet_write(pkt);
                led_from_pi = 3;
            }
        }
        if (rx_overflow != last_overflow) { last_overflow = rx_overflow; led_err = 10; }
        led_task();
    }
}
