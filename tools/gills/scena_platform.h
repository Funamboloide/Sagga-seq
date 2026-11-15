/* SCENA on the Ksoloti Gills: the knobs, the buttons and the LEDs as the ksoloti/gills objects read them
 * (pot p: adcvalues[0 1 2 3 6 7 8 9 11 12], button: PB5 PA10 PB12 PB13, led: LED3 PB3 PB4, LED4 PB6 PB7).
 * Class-body code, before the engine. SPDX-License-Identifier: GPL-3.0-only */
static int hw_adc(int i) {
    static const uint8_t ch[10] = {0, 1, 2, 3, 6, 7, 8, 9, 11, 12};
    return adcvalues[ch[i]];
}
static int hw_btn(int i) {
    switch (i) {
        case 0: return palReadPad(GPIOB, 5);
        case 1: return palReadPad(GPIOA, 10);
        case 2: return palReadPad(GPIOB, 12);
        default: return palReadPad(GPIOB, 13);
    }
}
static void hw_led(int i, bool on) {
    switch (i) {
        case 0: palWritePad(GPIOB, 3, on ? 1 : 0); break;     /* LED 3 blue */
        case 1: palWritePad(GPIOB, 4, on ? 1 : 0); break;     /* LED 3 red */
        case 2: palWritePad(GPIOB, 6, on ? 1 : 0); break;     /* LED 4 blue */
        default: palWritePad(GPIOB, 7, on ? 1 : 0); break;    /* LED 4 red */
    }
}
static void hw_setup() {
    palSetPadMode(GPIOB, 5, PAL_MODE_INPUT);
    palSetPadMode(GPIOA, 10, PAL_MODE_INPUT);
    palSetPadMode(GPIOB, 12, PAL_MODE_INPUT);
    palSetPadMode(GPIOB, 13, PAL_MODE_INPUT);
    palSetPadMode(GPIOB, 3, PAL_MODE_OUTPUT_PUSHPULL);
    palSetPadMode(GPIOB, 4, PAL_MODE_OUTPUT_PUSHPULL);
    palSetPadMode(GPIOB, 6, PAL_MODE_OUTPUT_PUSHPULL);
    palSetPadMode(GPIOB, 7, PAL_MODE_OUTPUT_PUSHPULL);
}
