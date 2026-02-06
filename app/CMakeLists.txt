cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr)
project(my_zephyr_test_app)

target_sources(app PRIVATE src/main.c)

# TODO
#set(SHIELD x_nucleo_iks01a1)