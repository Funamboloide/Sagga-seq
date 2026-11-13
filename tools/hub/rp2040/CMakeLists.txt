# SAGGA HUB PC port for the RP2040-Zero. Needs the Pico SDK: PICO_SDK_PATH in the environment, or the SDK's
# pico_sdk_import.cmake next to this file (README.md).
cmake_minimum_required(VERSION 3.13)
set(PICO_BOARD waveshare_rp2040_zero CACHE STRING "board")
include(pico_sdk_import.cmake)
project(sagga_pc C CXX ASM)
set(CMAKE_C_STANDARD 11)
pico_sdk_init()
add_executable(sagga_pc sagga_pc.c usb_descriptors.c)
target_include_directories(sagga_pc PRIVATE ${CMAKE_CURRENT_LIST_DIR})
target_link_libraries(sagga_pc pico_stdlib pico_unique_id hardware_uart tinyusb_device tinyusb_board)
pico_add_extra_outputs(sagga_pc)
