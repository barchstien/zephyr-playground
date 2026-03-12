/*
 * Copyright (c) 2016 Intel Corporation
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <stdio.h>
#include <zephyr/kernel.h>
//#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/logging/log.h>
#include <zephyr/net/socket.h>
#include <zephyr/rtio/rtio.h>

#include <zephyr/drivers/sensor/vl53l8cx.h>

LOG_MODULE_REGISTER(playground_app, LOG_LEVEL_INF);

// debug
//#include <zephyr/sys/printk.h>
//#include "vl53l8cx_debug.h"

#define DEFAULT_SAMPLE_FREQ_HZ 15
#define DEFAULT_ZONE_CNT 64

#define MAX_ZONE_CNT 64

#define DEST_PORT 5005
#define DEST_ADDR "192.168.1.176"

/* 
 * 1. Define RTIO context with a dedicated Memory Pool.
 * Args: name, sq_size (pow 2), cq_size (pow 2), mem_blocks, block_byte_size, alignment 
 */
RTIO_DEFINE_WITH_MEMPOOL(
    vl53l8cx_rtio_ctx,           // name
    8,                      // submission
    8,                      // completion
    16,                     // num of blocks
    VL53L8CX_SENSOR_READ_BLOCK_SIZE,
    sizeof(void *)          // byte aligned
);

#define VL53L8CX_STREAM
#ifdef VL53L8CX_STREAM
SENSOR_DT_STREAM_IODEV(
    vl53l8cx_iodev, 
    DT_INST(0, st_vl53l8cx), 
    { SENSOR_CHAN_DISTANCE, 0 }
);
#else
SENSOR_DT_READ_IODEV(
    vl53l8cx_iodev, 
    DT_INST(0, st_vl53l8cx), 
    { SENSOR_CHAN_DISTANCE, 0 }
);
#endif

void wait_and_read(const struct sensor_decoder_api *decoder, int sock,
                    struct sockaddr_in *dest_addr) {
    struct rtio_cqe *cqe;
    uint8_t *sensor_data_buff;
	uint32_t sensor_data_buff_len;
    struct sensor_chan_spec ch_spec = { SENSOR_CHAN_DISTANCE, 0 };
    static struct vl53l8cx_result_data result;
    int ret;

    // wait for a completion event
    cqe = rtio_cqe_consume_block(&vl53l8cx_rtio_ctx);
    if (cqe->result < 0) {
        LOG_ERR("cqe failed with result: %d", cqe->result);
        rtio_cqe_release(&vl53l8cx_rtio_ctx, cqe);
        return;
    }

    // Get data from completion queue element
    ret = rtio_cqe_get_mempool_buffer(&vl53l8cx_rtio_ctx, cqe, &sensor_data_buff, &sensor_data_buff_len);
    if (ret == 0) {
        // decode the data, always comes 1 by 1
        uint32_t fit = 0;
        ret = decoder->decode(sensor_data_buff, ch_spec, &fit, 1, &result);
        rtio_release_buffer(&vl53l8cx_rtio_ctx, sensor_data_buff, sensor_data_buff_len);
        
        // inverse image
        q15_t tmp[64];
        memcpy(tmp, result.readings[0].distance_mm, sizeof(q15_t[64]));
        for (int i=0; i<8; i++) {
            for (int j=0; j<8; j++) {
                result.readings[0].distance_mm[8*i + j] = tmp[8*(i+1) - (j + 1)];
            }
        }

        // send to UDP
        ret = zsock_sendto(
            sock, 
            (uint8_t*)(&result), 
            sizeof(struct vl53l8cx_result_data), 
            0, 
            (struct sockaddr*)dest_addr, 
            sizeof(struct sockaddr_in)
        );
        if (ret < 0) {
            LOG_ERR("UDP sendto failed errno:%d", errno);
        }
    }
    rtio_cqe_release(&vl53l8cx_rtio_ctx, cqe);
}

int main(void)
{
	int ret;
    //const uint32_t BUFF_DEBUG_SIZE = 100;
    //uint8_t buff[BUFF_DEBUG_SIZE];

	//printk("RAW PRINTK: Entering main\n");

	LOG_INF("START ---- CONFIG_SYS_CLOCK_TICKS_PER_SEC:%d", CONFIG_SYS_CLOCK_TICKS_PER_SEC);

	const struct device *dev = DEVICE_DT_GET_ONE(st_vl53l8cx);

    if (!device_is_ready(dev)) {
        LOG_INF("dev NOT ready");
        return 0;
    }
	LOG_INF("%s ready", dev->name);

    // resolution
    struct sensor_value resolution = { .val1 = DEFAULT_ZONE_CNT, .val2 = 0 };
    LOG_INF("Setting resolution to %d Hz...", resolution.val1);
    ret = sensor_attr_set(
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

    // sample freq
    struct sensor_value sample_freq = { .val1 = DEFAULT_SAMPLE_FREQ_HZ, .val2 = 0 };
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

    // decoder
    const struct sensor_decoder_api *decoder;
    sensor_get_decoder(dev, &decoder);

    // UDP
    int sock;
    struct sockaddr_in dest_addr;
    sock = zsock_socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) {
        LOG_ERR("Failed to create socket: %d", errno);
        return -EIO;
    }
    // destination address
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(DEST_PORT);
    zsock_inet_pton(AF_INET, DEST_ADDR, &dest_addr.sin_addr);

    //// main loop
#ifdef VL53L8CX_STREAM
    //// streaming
    struct rtio_sqe *sqe;
    // sensor_stream
    LOG_INF("sensor_stream()...");
    sensor_stream(&vl53l8cx_iodev, &vl53l8cx_rtio_ctx, NULL, &sqe);
    while (true) {
        wait_and_read(decoder, sock, &dest_addr);
    }
#else
    //// one-shot in a loop
    while (true) {
		ret = sensor_read_async_mempool(&vl53l8cx_iodev, &vl53l8cx_rtio_ctx, NULL);
		if (ret < 0) {
			LOG_ERR("Failed to submit read: %d", ret);
			continue;
		}
        wait_and_read(decoder, sock, &dest_addr);
        // TODO go to sleep, wake up, etc)
        k_msleep(1000);
    }
#endif
    zsock_close(sock);

}
