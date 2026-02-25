/*
 * Copyright (c) 2016 Intel Corporation
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <stdio.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/sensor.h>
//#include <zephyr/drivers/gpio.h>

#include <zephyr/logging/log.h>


LOG_MODULE_REGISTER(playground_app, LOG_LEVEL_INF);
// debug
//#include <zephyr/sys/printk.h>
#include "vl53l8cx_debug.h"

int main(void)
{
	int ret;
    const uint32_t BUFF_DEBUG_SIZE = 100;
    uint8_t buff[BUFF_DEBUG_SIZE];

	//printk("RAW PRINTK: Entering main\n");

	LOG_INF("START ----");

	const struct device *dev = DEVICE_DT_GET_ONE(st_vl53l8cx);

    if (!device_is_ready(dev)) {
        LOG_INF("dev NOT ready");
        return 0;
    }
	LOG_INF("%s ready", dev->name);

    // sample freq
    struct sensor_value sample_freq = { .val1 = 15, .val2 = 0 };
    LOG_INF("Setting frequency to %d Hz...", sample_freq.val1);
    ret = sensor_attr_set(
        dev, 
        SENSOR_CHAN_DISTANCE, 
        SENSOR_ATTR_SAMPLING_FREQUENCY, 
        &sample_freq
    );
    if (ret != 0) {
        LOG_ERR("Failed to set sample frequency (error %d)", ret);
    }
    ret = sensor_attr_get(
        dev, 
        SENSOR_CHAN_DISTANCE, 
        SENSOR_ATTR_SAMPLING_FREQUENCY, 
        &sample_freq
    );
    if (ret != 0) {
        LOG_ERR("Failed to get sample frequency (error %d)", ret);
    }
    LOG_INF("Read back sample freq: %d", sample_freq.val1);

    // resolution
    struct sensor_value resolution = { .val1 = 16, .val2 = 0 };
    LOG_INF("Setting resolution to %d Hz...", resolution.val1);
    sensor_attr_set(
        dev, 
        SENSOR_CHAN_DISTANCE, 
        SENSOR_ATTR_RESOLUTION, 
        &resolution
    );
    if (ret != 0) {
        LOG_ERR("Failed to set resolution (error %d)", ret);
    }

    ret = sensor_attr_get(
        dev, 
        SENSOR_CHAN_DISTANCE, 
        SENSOR_ATTR_RESOLUTION, 
        &resolution
    );
    if (ret != 0) {
        LOG_ERR("Failed to get resolution (error %d)", ret);
    }
    LOG_INF("Read back resolution: %d", resolution.val1);
    ///////////////////////////////////////////////////////////////
#if 0
    /* 2. PREPARE: Get Standard Decoder */
    const struct sensor_decoder_api *decoder;
    sensor_get_decoder(dev, &decoder);

    uint8_t raw_buffer[128]; // Allocate stack buffer for 8x8

    while (1) {
        /* 3. EXECUTE: Call your CUSTOM driver helper */
        /* This keeps I2C logic inside the driver, but runs synchronously */
        my_lidar_manual_read(dev, raw_buffer, sizeof(raw_buffer));

        /* 4. DECODE: Use Standard Decoder */
        struct sensor_value point_cloud[64];
        uint32_t fit = 0;
        
        decoder->decode(raw_buffer, SENSOR_CHAN_DISTANCE, 
                        &fit, 64, point_cloud);

        printk("Zone 0: %d\n", point_cloud[0].val1);
        k_msleep(100);
    }
#endif
    ///////////////////////////////////////////////////////////////

    while (true) {
        //k_msleep(10000);
        //LOG_INF("mmmmmmmmm ----");
        test_read(dev, buff, BUFF_DEBUG_SIZE);
    }
	return 0;
}
