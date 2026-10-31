/********************************************************************************************************
 * @file    app_adv.c
 *
 * @brief   Superascher: Advertising mit wechselndem Takt und Zählerstand in den Werbedaten
 *
 *******************************************************************************************************/
#include "tl_common.h"
#include "drivers.h"
#include "stack/ble/ble.h"

#include "app_adv.h"


// Ruhe: alle 2 s reicht, nach jedem Stempeln sendet er ohnehin 30 s lang schnell
#define ADV_IDLE_INTERVAL				ADV_INTERVAL_2S
#define ADV_FAST_INTERVAL				ADV_INTERVAL_100MS
#define ADV_FAST_DURATION_US			(30 * 1000 * 1000)	//max. 268 s (Überlauf System-Timer)

/* 29 Byte: Flags (3) + 128-bit Service-UUID (18) + Manufacturer Data (8).
 * Company ID 0xFFFF = "nur zum Testen" laut Bluetooth SIG, für ein Produkt eine eigene beantragen. */
#define ADV_COUNT_OFFSET				25
_attribute_ble_data_retention_	static u8 adv_data[29] = {
	 2,  DT_FLAGS,								0x06,	// LE general discoverable, BR/EDR not supported
	17,  DT_COMPLETE_LIST_128BIT_SERVICE_UUID,	0x74,0x7b,0x13,0xa8,0xaf,0x44,0x88,0x85,0x0f,0x46,0x39,0x0f,0x01,0x00,0x77,0x15,
	 7,  DATA_TYPE_MANUFACTURER_SPECIFIC_DATA,	0xFF,0xFF,	0,0,0,0,	// Company ID, u32 Zählerstand (little endian)
};

static const u8 scan_rsp[] = {
	 9,  DT_COMPLETE_LOCAL_NAME, 				'B','u','t','t',' ','B','i','n',
};

_attribute_ble_data_retention_	static u8  adv_fast;
_attribute_ble_data_retention_	static u32 adv_fast_tick;


static void adv_set_count(u32 count)
{
	adv_data[ADV_COUNT_OFFSET + 0] = U32_BYTE0(count);
	adv_data[ADV_COUNT_OFFSET + 1] = U32_BYTE1(count);
	adv_data[ADV_COUNT_OFFSET + 2] = U32_BYTE2(count);
	adv_data[ADV_COUNT_OFFSET + 3] = U32_BYTE3(count);
}

static void adv_apply(adv_inter_t interval)
{
	blc_ll_setAdvEnable(BLC_ADV_DISABLE);
	blc_ll_setAdvData(adv_data, sizeof(adv_data));
	blc_ll_setAdvParam(interval, interval, ADV_TYPE_CONNECTABLE_UNDIRECTED, OWN_ADDRESS_PUBLIC, 0, NULL, BLT_ENABLE_ADV_ALL, ADV_FP_NONE);
	blc_ll_setAdvEnable(BLC_ADV_ENABLE);
}


void app_adv_init(u32 count)
{
	adv_set_count(count);
	blc_ll_setScanRspData((u8 *)scan_rsp, sizeof(scan_rsp));
	adv_fast = 0;
	adv_apply(ADV_IDLE_INTERVAL);
}


void app_adv_burst(u32 count)
{
	adv_set_count(count);
	adv_fast = 1;
	adv_fast_tick = clock_time();
	adv_apply(ADV_FAST_INTERVAL);
}


void app_adv_loop(void)
{
	if(adv_fast && clock_time_exceed(adv_fast_tick, ADV_FAST_DURATION_US)){
		adv_fast = 0;
		adv_apply(ADV_IDLE_INTERVAL);
	}
}


int app_adv_is_fast(void)
{
	return adv_fast;
}
