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


LOG_MODULE_REGISTER(playground_app, LOG_LEVEL_INF);
// debug
//#include <zephyr/sys/printk.h>
#include "vl53l8cx_debug.h"

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
    tof_rtio_ctx,           // name
    2,//8,                      // sq size
    2,//8,                      // cq size
    4,//16,                     // num of blocks
    sizeof(VL53L8CX_ResultsData) + 5,// 1 byte (num of zone) + 4 bytes timepoint msec + 2 bytes per zone
    sizeof(void *)          // byte aligne
);

SENSOR_DT_READ_IODEV(
    tof_iodev, 
    DT_INST(0, st_vl53l8cx), 
    { SENSOR_CHAN_DISTANCE, 0 }
);

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

    // sample freq, starts sampling if freq > 0
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
    // 1. Create a UDP socket (AF_INET = IPv4, SOCK_DGRAM = UDP)
    sock = zsock_socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) {
        LOG_ERR("Failed to create socket: %d", errno);
        return -51;
    }
    // 2. Setup destination address
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(DEST_PORT);
    zsock_inet_pton(AF_INET, DEST_ADDR, &dest_addr.sin_addr);
    

#if 1
    // trigger
    //struct sensor_trigger trig = {
    //    .type = SENSOR_TRIG_DATA_READY,
    //    .chan = SENSOR_CHAN_DISTANCE,
    //};
    ///* Register the ISR */
    //if (sensor_trigger_set(dev, &trig, vl53l8cx_rdy_callback) < 0) {
    //    return -EIO;
    //}
    ///////////////////////////////////////////////////////////////
    ///////////////////////////////////////////////////////////////
    struct rtio_cqe *cqe;
    uint8_t *buf;
	uint32_t buf_len;
    struct sensor_chan_spec ch_spec = { SENSOR_CHAN_DISTANCE, 0 };
    uint8_t data_out[1+4+64*2]; // TODO 
    uint8_t data_tmp[1+4+64*2];
    int i = 0;

    for (i=0; i<1000000; i++) {
        /* Queue async read to the RTIO context; uses RTIO mempool for allocation */
		ret = sensor_read_async_mempool(&tof_iodev, &tof_rtio_ctx, NULL);
		if (ret < 0) {
			LOG_ERR("Failed to submit read: %d", ret);
			continue;
		}

#if 0
        /* Block and consume the completion event */
		cqe = rtio_cqe_consume_block(&tof_rtio_ctx);
#endif
        //cqe = rtio_cqe_consume(&tof_rtio_ctx);
        //while (cqe == 0) {
        //    //LOG_INF(" ... ");
        //    k_sleep(K_MSEC(1));
        //    cqe = rtio_cqe_consume(&tof_rtio_ctx);
        //}
        cqe = rtio_cqe_consume_block(&tof_rtio_ctx);
        // what about using this:
        // Wait up to 500ms for exactly 1 completion event
        //int copied = rtio_cqe_copy_out(&tof_rtio_ctx, &cqe, 1, K_MSEC(500));

        
        //LOG_INF("Got CQE !");

		if (cqe->result < 0) {
			LOG_ERR(" *** Read failed with result: %d", cqe->result);
			rtio_cqe_release(&tof_rtio_ctx, cqe);
			continue;
		}

		/* Pull buffer pointer generated by the driver's rx_buf pool execution */
		ret = rtio_cqe_get_mempool_buffer(&tof_rtio_ctx, cqe, &buf, &buf_len);
		if (ret == 0) {
			uint32_t fit = 0;
			ret = decoder->decode(buf, ch_spec, &fit, 1, &data_tmp);
            rtio_release_buffer(&tof_rtio_ctx, buf, buf_len);
            // header
            memcpy(data_out, data_tmp, 5);
            // inverse image
#if 1
            uint16_t *src = (int16_t*)(&data_tmp[5]);
            uint16_t *dst = (int16_t*)(&data_out[5]);
            for (int i=0; i<8; i++) {
                for (int j=0; j<8; j++) {
                    dst[8*i + j] = src[8*(i+1) - (j + 1)];
                    //dst[i*8+j] = src[i*8+j];
                }
            }
#else
            memcpy(data_out + 5, data_tmp + 5, 64*2);
#endif

#if 0
            /////
            // Use [0 : 99] cm
            //printk("blop %d", ret);
            uint8_t pretty[200];
            memset(pretty, 0, sizeof(pretty));
            uint8_t ind = 0;
            for (int i=0; i<64; i++) {
                // mm -> cm
                data_out[i] =  data_out[i] / 10;
                if (data_out[i] >= 100) { data_out[i] = 99; }
                if (i % 8 == 0) {
                    //printk("\n");
                    snprintf(pretty + ind, sizeof(pretty) - ind, "\n");
                    ind += 1;
                }
                //printk("%d%d ", data_out[i]/10, data_out[i]%10);
                if (data_out[i] == 99)
                    snprintf(pretty + ind, sizeof(pretty) - ind, "   ");
                else
                    snprintf(pretty + ind, sizeof(pretty) - ind, "%d%d ", data_out[i]/10, data_out[i]%10);
                ind += 3;
            }
            //printk("\n");
            snprintf(pretty + ind, sizeof(pretty) - ind, "\n");
            ind += 1;
            //LOG_INF("%s", pretty);
            printf("%s\n", pretty);
#endif
            int data_out_size = 1 + 4 + 64*2; // TODO
            zsock_sendto(
                sock, data_out, data_out_size, 0, 
                (struct sockaddr *)&dest_addr, sizeof(dest_addr)
            );

			
		}

		rtio_cqe_release(&tof_rtio_ctx, cqe);
        //LOG_INF("------");
		//k_sleep(K_MSEC(10));
        //k_sleep(K_MSEC(250));
    }
    // stop sampling
    sample_freq.val1 = 0;
    ret = sensor_attr_set(
        dev, 
        SENSOR_CHAN_DISTANCE, 
        SENSOR_ATTR_SAMPLING_FREQUENCY, 
        &sample_freq
    );
#endif

    zsock_close(sock);

#if 0
    while (true) {
        //k_msleep(10000);
        //LOG_INF("mmmmmmmmm ----");
        test_read(dev, buff, BUFF_DEBUG_SIZE);
    }
	return 0;
#endif
}
