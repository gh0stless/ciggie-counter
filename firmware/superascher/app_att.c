/********************************************************************************************************
 * @file    app_att.c
 *
 * @brief   This is the source file for BLE SDK
 *
 * @author  BLE GROUP
 * @date    2020.06
 *
 * @par     Copyright (c) 2020, Telink Semiconductor (Shanghai) Co., Ltd. ("TELINK")
 *
 *          Licensed under the Apache License, Version 2.0 (the "License");
 *          you may not use this file except in compliance with the License.
 *          You may obtain a copy of the License at
 *
 *              http://www.apache.org/licenses/LICENSE-2.0
 *
 *          Unless required by applicable law or agreed to in writing, software
 *          distributed under the License is distributed on an "AS IS" BASIS,
 *          WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *          See the License for the specific language governing permissions and
 *          limitations under the License.
 *
 *******************************************************************************************************/
#include "tl_common.h"
#include "drivers.h"
#include "stack/ble/ble.h"

#include "app.h"
#include "app_att.h"
#include "app_ui.h"
#include "app_log.h"

#include "application/usbstd/usbkeycode.h"
#include "application/keyboard/keyboard.h"
#include "application/rf_frame.h"



////////////////////////////////////////// slave-role ATT service concerned ///////////////////////////////////////////////
typedef struct
{
  /** Minimum value for the connection event (interval. 0x0006 - 0x0C80 * 1.25 ms) */
  u16 intervalMin;
  /** Maximum value for the connection event (interval. 0x0006 - 0x0C80 * 1.25 ms) */
  u16 intervalMax;
  /** Number of LL latency connection events (0x0000 - 0x03e8) */
  u16 latency;
  /** Connection Timeout (0x000A - 0x0C80 * 10 ms) */
  u16 timeout;
} gap_periConnectParams_t;

typedef struct{
	u8	type;
	u8  rf_len;
	u16	l2capLen;
	u16	chanId;
	u8  opcode;
	u16 handle;
	u8 value;
}ble_rf_packet_att_write_t;

static const u16 clientCharacterCfgUUID = GATT_UUID_CLIENT_CHAR_CFG;

static const u16 extReportRefUUID = GATT_UUID_EXT_REPORT_REF;

static const u16 reportRefUUID = GATT_UUID_REPORT_REF;

static const u16 userdesc_UUID	= GATT_UUID_CHAR_USER_DESC;

static const u16 serviceChangeUUID = GATT_UUID_SERVICE_CHANGE;

static const u16 my_primaryServiceUUID = GATT_UUID_PRIMARY_SERVICE;

static const u16 my_characterUUID = GATT_UUID_CHARACTER;

static const u16 my_devServiceUUID = SERVICE_UUID_DEVICE_INFORMATION;

static const u16 my_PnPUUID = CHARACTERISTIC_UUID_PNP_ID;

static const u16 my_devNameUUID = GATT_UUID_DEVICE_NAME;

static const u16 my_gapServiceUUID = SERVICE_UUID_GENERIC_ACCESS;

static const u16 my_appearanceUIID = GATT_UUID_APPEARANCE;

static const u16 my_periConnParamUUID = GATT_UUID_PERI_CONN_PARAM;

static const u16 my_appearance = GAP_APPEARE_UNKNOWN;

static const u16 my_gattServiceUUID = SERVICE_UUID_GENERIC_ATTRIBUTE;

static const gap_periConnectParams_t my_periConnParameters = {20, 40, 0, 1000};

_attribute_ble_data_retention_	static u16 serviceChangeVal[2] = {0};

_attribute_ble_data_retention_	static u8 serviceChangeCCC[2] = {0,0};

static const u8 my_devName[] = {'B','u','t','t',' ','B','i','n'};

static const u8 my_PnPtrs [] = {0x02, 0x8a, 0x24, 0x66, 0x82, 0x01, 0x00};

//////////////////////// Battery /////////////////////////////////////////////////
static const u16 my_batServiceUUID        = SERVICE_UUID_BATTERY;
static const u16 my_batCharUUID       	  = CHARACTERISTIC_UUID_BATTERY_LEVEL;
_attribute_ble_data_retention_	static u8 batteryValueInCCC[2] = {0,0};
_attribute_ble_data_retention_	static u8 my_batVal[1] 	= {99};

//////////////////////// Superascher /////////////////////////////////////////////
// Service 15770001-, Count 15770002-, Time 15770003-, Events 15770004-0f39-460f-8588-44afa8137b74 (Bytes little endian)
#define SUPERASCHER_UUID_SERVICE	0x74,0x7b,0x13,0xa8,0xaf,0x44,0x88,0x85,0x0f,0x46,0x39,0x0f,0x01,0x00,0x77,0x15
#define SUPERASCHER_UUID_COUNT		0x74,0x7b,0x13,0xa8,0xaf,0x44,0x88,0x85,0x0f,0x46,0x39,0x0f,0x02,0x00,0x77,0x15
#define SUPERASCHER_UUID_TIME		0x74,0x7b,0x13,0xa8,0xaf,0x44,0x88,0x85,0x0f,0x46,0x39,0x0f,0x03,0x00,0x77,0x15
#define SUPERASCHER_UUID_EVENTS		0x74,0x7b,0x13,0xa8,0xaf,0x44,0x88,0x85,0x0f,0x46,0x39,0x0f,0x04,0x00,0x77,0x15

static const u8 my_superascherServiceUUID[16]	= {SUPERASCHER_UUID_SERVICE};
static const u8 my_superascherCountUUID[16]		= {SUPERASCHER_UUID_COUNT};
_attribute_ble_data_retention_	static u8 superascherCount[4]		= {0,0,0,0};
_attribute_ble_data_retention_	static u8 superascherCountCCC[2]	= {0,0};
static const u8 my_superascherCountName[] = {'C','o','u','n','t'};
static const u8 my_superascherTimeUUID[16]		= {SUPERASCHER_UUID_TIME};
_attribute_ble_data_retention_	static u8 superascherTime[4]		= {0,0,0,0};
static const u8 my_superascherTimeName[] = {'T','i','m','e'};
static const u8 my_superascherEventsUUID[16]	= {SUPERASCHER_UUID_EVENTS};
_attribute_ble_data_retention_	static u8 superascherEvents[4]		= {0,0,0,0};
_attribute_ble_data_retention_	static u8 superascherEventsCCC[2]	= {0,0};
static const u8 my_superascherEventsName[] = {'E','v','e','n','t','s'};


//////////////////////// OTA //////////////////////////////////
static const  u8 my_OtaServiceUUID[16]				= WRAPPING_BRACES(TELINK_OTA_UUID_SERVICE);
static const  u8 my_OtaUUID[16]						= WRAPPING_BRACES(TELINK_SPP_DATA_OTA);
_attribute_ble_data_retention_	static 		  u8 my_OtaDataCCC[2] = {0,0};
_attribute_ble_data_retention_	static 		  u8 my_OtaData 						= 0x00;
static const u8  my_OtaName[] = {'O', 'T', 'A'};


//// GAP attribute values
static const u8 my_devNameCharVal[5] = {
	CHAR_PROP_READ,
	U16_LO(GenericAccess_DeviceName_DP_H), U16_HI(GenericAccess_DeviceName_DP_H),
	U16_LO(GATT_UUID_DEVICE_NAME), U16_HI(GATT_UUID_DEVICE_NAME)
};
static const u8 my_appearanceCharVal[5] = {
	CHAR_PROP_READ,
	U16_LO(GenericAccess_Appearance_DP_H), U16_HI(GenericAccess_Appearance_DP_H),
	U16_LO(GATT_UUID_APPEARANCE), U16_HI(GATT_UUID_APPEARANCE)
};
static const u8 my_periConnParamCharVal[5] = {
	CHAR_PROP_READ,
	U16_LO(CONN_PARAM_DP_H), U16_HI(CONN_PARAM_DP_H),
	U16_LO(GATT_UUID_PERI_CONN_PARAM), U16_HI(GATT_UUID_PERI_CONN_PARAM)
};


//// GATT attribute values
static const u8 my_serviceChangeCharVal[5] = {
	CHAR_PROP_INDICATE,
	U16_LO(GenericAttribute_ServiceChanged_DP_H), U16_HI(GenericAttribute_ServiceChanged_DP_H),
	U16_LO(GATT_UUID_SERVICE_CHANGE), U16_HI(GATT_UUID_SERVICE_CHANGE)
};


//// device Information  attribute values
static const u8 my_PnCharVal[5] = {
	CHAR_PROP_READ,
	U16_LO(DeviceInformation_pnpID_DP_H), U16_HI(DeviceInformation_pnpID_DP_H),
	U16_LO(CHARACTERISTIC_UUID_PNP_ID), U16_HI(CHARACTERISTIC_UUID_PNP_ID)
};


//// Superascher attribute values
static const u8 my_superascherCountCharVal[19] = {
	CHAR_PROP_READ | CHAR_PROP_NOTIFY,
	U16_LO(SUPERASCHER_COUNT_DP_H), U16_HI(SUPERASCHER_COUNT_DP_H),
	SUPERASCHER_UUID_COUNT
};
static const u8 my_superascherTimeCharVal[19] = {
	CHAR_PROP_READ | CHAR_PROP_WRITE,
	U16_LO(SUPERASCHER_TIME_DP_H), U16_HI(SUPERASCHER_TIME_DP_H),
	SUPERASCHER_UUID_TIME
};
static const u8 my_superascherEventsCharVal[19] = {
	CHAR_PROP_WRITE | CHAR_PROP_NOTIFY,
	U16_LO(SUPERASCHER_EVENTS_DP_H), U16_HI(SUPERASCHER_EVENTS_DP_H),
	SUPERASCHER_UUID_EVENTS
};

/* Write auf Time: u32 Unix-Zeit (little endian) stellt die Uhr */
int superascher_onTimeWrite(u16 connHandle, ble_rf_packet_att_write_t *p)
{
	u32 t;
	if(p->l2capLen - 3 == 4){
		memcpy(&t, &p->value, 4);
		app_log_set_time(t);
	}
	return 0;
}

/* Write auf Events: u32 Nummer (little endian), ab der die Ereignisse gesendet werden */
int superascher_onEventsWrite(u16 connHandle, ble_rf_packet_att_write_t *p)
{
	u32 from;
	if(p->l2capLen - 3 == 4){
		memcpy(&from, &p->value, 4);
		app_log_request(from);
	}
	return 0;
}


//// Battery attribute values
static const u8 my_batCharVal[5] = {
	CHAR_PROP_READ | CHAR_PROP_NOTIFY,
	U16_LO(BATT_LEVEL_INPUT_DP_H), U16_HI(BATT_LEVEL_INPUT_DP_H),
	U16_LO(CHARACTERISTIC_UUID_BATTERY_LEVEL), U16_HI(CHARACTERISTIC_UUID_BATTERY_LEVEL)
};


//// OTA attribute values
static const u8 my_OtaCharVal[19] = {
	CHAR_PROP_READ | CHAR_PROP_WRITE_WITHOUT_RSP | CHAR_PROP_NOTIFY,
	U16_LO(OTA_CMD_OUT_DP_H), U16_HI(OTA_CMD_OUT_DP_H),
	TELINK_SPP_DATA_OTA,
};

// TM : to modify
static const attribute_t my_Attributes[] = {

	{ATT_END_H - 1, 0,0,0,0,0},	// total num of attribute


	// 0001 - 0007  gap
	{7,ATT_PERMISSIONS_READ,2,2,(u8*)(&my_primaryServiceUUID), 	(u8*)(&my_gapServiceUUID), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_devNameCharVal),(u8*)(&my_characterUUID), (u8*)(my_devNameCharVal), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_devName), (u8*)(&my_devNameUUID), (u8*)(my_devName), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_appearanceCharVal),(u8*)(&my_characterUUID), (u8*)(my_appearanceCharVal), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof (my_appearance), (u8*)(&my_appearanceUIID), 	(u8*)(&my_appearance), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_periConnParamCharVal),(u8*)(&my_characterUUID), (u8*)(my_periConnParamCharVal), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof (my_periConnParameters),(u8*)(&my_periConnParamUUID), 	(u8*)(&my_periConnParameters), 0},


	// 0008 - 000b gatt
	{4,ATT_PERMISSIONS_READ,2,2,(u8*)(&my_primaryServiceUUID), 	(u8*)(&my_gattServiceUUID), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_serviceChangeCharVal),(u8*)(&my_characterUUID), 		(u8*)(my_serviceChangeCharVal), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof (serviceChangeVal), (u8*)(&serviceChangeUUID), 	(u8*)(&serviceChangeVal), 0},
	{0,ATT_PERMISSIONS_RDWR,2,sizeof (serviceChangeCCC),(u8*)(&clientCharacterCfgUUID), (u8*)(serviceChangeCCC), 0},


	// 000c - 000e  device Information Service
	{3,ATT_PERMISSIONS_READ,2,2,(u8*)(&my_primaryServiceUUID), 	(u8*)(&my_devServiceUUID), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_PnCharVal),(u8*)(&my_characterUUID), (u8*)(my_PnCharVal), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof (my_PnPtrs),(u8*)(&my_PnPUUID), (u8*)(my_PnPtrs), 0},


	////////////////////////////////////// Superascher Service ///////////////////////////////////////////////
	{SUPERASCHER_EVENTS_DESC_H - SUPERASCHER_PS_H + 1,ATT_PERMISSIONS_READ,2,16,(u8*)(&my_primaryServiceUUID), 	(u8*)(&my_superascherServiceUUID), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_superascherCountCharVal),(u8*)(&my_characterUUID), (u8*)(my_superascherCountCharVal), 0},				//prop
	{0,ATT_PERMISSIONS_READ,16,sizeof(superascherCount),(u8*)(&my_superascherCountUUID), 	(u8*)(superascherCount), 0},	//value
	{0,ATT_PERMISSIONS_RDWR,2,sizeof(superascherCountCCC),(u8*)(&clientCharacterCfgUUID), 	(u8*)(superascherCountCCC), 0},	//value
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_superascherCountName),(u8*)(&userdesc_UUID), (u8*)(my_superascherCountName), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_superascherTimeCharVal),(u8*)(&my_characterUUID), (u8*)(my_superascherTimeCharVal), 0},				//prop
	{0,ATT_PERMISSIONS_RDWR,16,sizeof(superascherTime),(u8*)(&my_superascherTimeUUID), 	(u8*)(superascherTime), (att_readwrite_callback_t)&superascher_onTimeWrite},	//value
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_superascherTimeName),(u8*)(&userdesc_UUID), (u8*)(my_superascherTimeName), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_superascherEventsCharVal),(u8*)(&my_characterUUID), (u8*)(my_superascherEventsCharVal), 0},				//prop
	{0,ATT_PERMISSIONS_RDWR,16,sizeof(superascherEvents),(u8*)(&my_superascherEventsUUID), 	(u8*)(superascherEvents), (att_readwrite_callback_t)&superascher_onEventsWrite},	//value
	{0,ATT_PERMISSIONS_RDWR,2,sizeof(superascherEventsCCC),(u8*)(&clientCharacterCfgUUID), 	(u8*)(superascherEventsCCC), 0},	//value
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_superascherEventsName),(u8*)(&userdesc_UUID), (u8*)(my_superascherEventsName), 0},


	////////////////////////////////////// Battery Service /////////////////////////////////////////////////////
	// 002a - 002d
	{4,ATT_PERMISSIONS_READ,2,2,(u8*)(&my_primaryServiceUUID), 	(u8*)(&my_batServiceUUID), 0},
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_batCharVal),(u8*)(&my_characterUUID), (u8*)(my_batCharVal), 0},				//prop
	{0,ATT_PERMISSIONS_READ,2,sizeof(my_batVal),(u8*)(&my_batCharUUID), 	(u8*)(my_batVal), 0},	//value
	{0,ATT_PERMISSIONS_RDWR,2,sizeof(batteryValueInCCC),(u8*)(&clientCharacterCfgUUID), 	(u8*)(batteryValueInCCC), 0},	//value


	////////////////////////////////////// OTA /////////////////////////////////////////////////////
	// 0036 - 0039
	{5,ATT_PERMISSIONS_READ, 2,16,(u8*)(&my_primaryServiceUUID), 	(u8*)(&my_OtaServiceUUID), 0},
	{0,ATT_PERMISSIONS_READ, 2, sizeof(my_OtaCharVal),(u8*)(&my_characterUUID), (u8*)(my_OtaCharVal), 0},				//prop
	{0,ATT_PERMISSIONS_RDWR,16,sizeof(my_OtaData),(u8*)(&my_OtaUUID),	(&my_OtaData), &otaWrite, NULL},			//value
	{0,ATT_PERMISSIONS_RDWR,2,sizeof(my_OtaDataCCC),(u8*)(&clientCharacterCfgUUID), 	(u8*)(my_OtaDataCCC), 0},	//value
	{0,ATT_PERMISSIONS_READ, 2,sizeof (my_OtaName),(u8*)(&userdesc_UUID), (u8*)(my_OtaName), 0},

};

/**
 * @brief   GATT initialization.
 *          !!!Note: this function is used to register ATT table to BLE Stack.
 * @param   none.
 * @return  none.
 */
void	my_gatt_init (void)
{
	bls_att_setAttributeTable ((u8 *)my_Attributes);
}


/**
 * @brief   Zaehlerstand im GATT aktualisieren und per Notify senden (falls abonniert).
 * @param   count - neuer Zaehlerstand
 * @return  none.
 */
void app_att_set_count (u32 count)
{
	superascherCount[0] = U32_BYTE0(count);
	superascherCount[1] = U32_BYTE1(count);
	superascherCount[2] = U32_BYTE2(count);
	superascherCount[3] = U32_BYTE3(count);

	if(superascherCountCCC[0] & 0x01){  //Notify abonniert
		for(int i=ACL_CENTRAL_MAX_NUM; i < (ACL_CENTRAL_MAX_NUM + ACL_PERIPHR_MAX_NUM); i++){
			if(conn_dev_list[i].conn_state){
				blc_gatt_pushHandleValueNotify (conn_dev_list[i].conn_handle, SUPERASCHER_COUNT_DP_H, superascherCount, sizeof(superascherCount));
			}
		}
	}
}


/**
 * @brief   Angezeigte Uhrzeit (Characteristic Time) aktualisieren.
 * @param   unix_time - Unix-Zeit, 0 = nicht gestellt
 * @return  none.
 */
void app_att_set_time (u32 unix_time)
{
	superascherTime[0] = U32_BYTE0(unix_time);
	superascherTime[1] = U32_BYTE1(unix_time);
	superascherTime[2] = U32_BYTE2(unix_time);
	superascherTime[3] = U32_BYTE3(unix_time);
}


/**
 * @brief   Daten ueber die Characteristic Events senden (Notify).
 * @param   p   - Daten
 * @param   len - Laenge (max. 20 Byte)
 * @return  1 = gesendet, 0 = TX-FIFO voll (spaeter erneut), -1 = nicht verbunden oder nicht abonniert
 */
int app_att_send_events (u8 *p, int len)
{
	if(!(superascherEventsCCC[0] & 0x01)){
		return -1;
	}
	for(int i=ACL_CENTRAL_MAX_NUM; i < (ACL_CENTRAL_MAX_NUM + ACL_PERIPHR_MAX_NUM); i++){
		if(conn_dev_list[i].conn_state){
			return blc_gatt_pushHandleValueNotify (conn_dev_list[i].conn_handle, SUPERASCHER_EVENTS_DP_H, p, len) == BLE_SUCCESS ? 1 : 0;
		}
	}
	return -1;
}
