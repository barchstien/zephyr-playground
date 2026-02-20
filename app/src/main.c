/*
 * Copyright (c) 2016 Intel Corporation
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <stdio.h>
#include <zephyr/kernel.h>
//#include <zephyr/drivers/gpio.h>

#include <zephyr/logging/log.h>

//#include <zephyr/sys/printk.h>

LOG_MODULE_REGISTER(playground_app, LOG_LEVEL_INF);

int main(void)
{
	int ret;

	//printk("RAW PRINTK: Entering main\n");

	LOG_INF("START ----");

	const struct device *dev = DEVICE_DT_GET_ONE(st_vl53l8cx);

    LOG_INF("is dev ready");
    if (!device_is_ready(dev)) {
        LOG_INF("dev NOT ready");
        return 0;
    }
	LOG_INF("dev ready");

    //struct sensor_value val;
    //sensor_sample_fetch(dev);
    //sensor_channel_get(dev, SENSOR_CHAN_DISTANCE, &val);

	LOG_INF("STOP  ----");

    while (true) {
        k_msleep(3000);
        LOG_INF("mmmmmmmmm ----");
    }
	return 0;
}
