/********************************************************************************************************
 * @file    app_att.h
 *
 * @brief   This is the header file for BLE SDK
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
#ifndef BLM_ATT_H_
#define BLM_ATT_H_

#include "tl_common.h"


///////////////////////////////////// slave-role ATT service HANDLER define ///////////////////////////////////////
typedef enum
{
	ATT_H_START = 0,


	//// Gap ////
	/**********************************************************************************************/
	GenericAccess_PS_H, 					//UUID: 2800, 	VALUE: uuid 1800
	GenericAccess_DeviceName_CD_H,			//UUID: 2803, 	VALUE:  			Prop: Read | Notify
	GenericAccess_DeviceName_DP_H,			//UUID: 2A00,   VALUE: device name
	GenericAccess_Appearance_CD_H,			//UUID: 2803, 	VALUE:  			Prop: Read
	GenericAccess_Appearance_DP_H,			//UUID: 2A01,	VALUE: appearance
	CONN_PARAM_CD_H,						//UUID: 2803, 	VALUE:  			Prop: Read
	CONN_PARAM_DP_H,						//UUID: 2A04,   VALUE: connParameter


	//// gatt ////
	/**********************************************************************************************/
	GenericAttribute_PS_H,					//UUID: 2800, 	VALUE: uuid 1801
	GenericAttribute_ServiceChanged_CD_H,	//UUID: 2803, 	VALUE:  			Prop: Indicate
	GenericAttribute_ServiceChanged_DP_H,   //UUID:	2A05,	VALUE: service change
	GenericAttribute_ServiceChanged_CCB_H,	//UUID: 2902,	VALUE: serviceChangeCCC


	//// device information ////
	/**********************************************************************************************/
	DeviceInformation_PS_H,					//UUID: 2800, 	VALUE: uuid 180A
	DeviceInformation_pnpID_CD_H,			//UUID: 2803, 	VALUE:  			Prop: Read
	DeviceInformation_pnpID_DP_H,			//UUID: 2A50,	VALUE: PnPtrs


	//// Superascher ////
	/**********************************************************************************************/
	SUPERASCHER_PS_H,						//UUID: 2800, 	VALUE: superascher service uuid
	SUPERASCHER_COUNT_CD_H,					//UUID: 2803, 	VALUE:  			Prop: Read | Notify
	SUPERASCHER_COUNT_DP_H,					//UUID: superascher count uuid,  VALUE: u32 Zaehlerstand (little endian)
	SUPERASCHER_COUNT_CCB_H,				//UUID: 2902, 	VALUE: countCCC
	SUPERASCHER_COUNT_DESC_H,				//UUID: 2901, 	VALUE: countName
	SUPERASCHER_TIME_CD_H,					//UUID: 2803, 	VALUE:  			Prop: Read | Write
	SUPERASCHER_TIME_DP_H,					//UUID: superascher time uuid,  VALUE: u32 Unix-Zeit (0 = nicht gestellt)
	SUPERASCHER_TIME_DESC_H,				//UUID: 2901, 	VALUE: timeName
	SUPERASCHER_EVENTS_CD_H,				//UUID: 2803, 	VALUE:  			Prop: Write | Notify
	SUPERASCHER_EVENTS_DP_H,				//UUID: superascher events uuid,  VALUE: Write u32 ab-Nummer, Notify Ereignisse
	SUPERASCHER_EVENTS_CCB_H,				//UUID: 2902, 	VALUE: eventsCCC
	SUPERASCHER_EVENTS_DESC_H,				//UUID: 2901, 	VALUE: eventsName


	//// battery service ////
	/**********************************************************************************************/
	BATT_PS_H, 								//UUID: 2800, 	VALUE: uuid 180f
	BATT_LEVEL_INPUT_CD_H,					//UUID: 2803, 	VALUE:  			Prop: Read | Notify
	BATT_LEVEL_INPUT_DP_H,					//UUID: 2A19 	VALUE: batVal
	BATT_LEVEL_INPUT_CCB_H,					//UUID: 2902, 	VALUE: batValCCC

	//// Ota ////
	/**********************************************************************************************/
	OTA_PS_H, 								//UUID: 2800, 	VALUE: telink ota service uuid
	OTA_CMD_OUT_CD_H,						//UUID: 2803, 	VALUE:  			Prop: read | write_without_rsp | notify
	OTA_CMD_OUT_DP_H,						//UUID: telink ota uuid,  VALUE: otaData
	OTA_CMD_OUT_CCB_H,						//UUID: 2902, 	VALUE: my_OtaDataCCC
	OTA_CMD_OUT_DESC_H,						//UUID: 2901, 	VALUE: otaName


	ATT_END_H,

}ATT_HANDLE;





/**
 * @brief   GATT initialization.
 *          !!!Note: this function is used to register ATT table to BLE Stack.
 * @param   none.
 * @return  none.
 */
void my_gatt_init (void);

/**
 * @brief   Zaehlerstand im GATT aktualisieren und per Notify senden (falls abonniert).
 * @param   count - neuer Zaehlerstand
 * @return  none.
 */
void app_att_set_count (u32 count);

/**
 * @brief   Angezeigte Uhrzeit (Characteristic Time) aktualisieren.
 * @param   unix_time - Unix-Zeit, 0 = nicht gestellt
 * @return  none.
 */
void app_att_set_time (u32 unix_time);

/**
 * @brief   Daten ueber die Characteristic Events senden (Notify).
 * @param   p   - Daten
 * @param   len - Laenge (max. 20 Byte)
 * @return  1 = gesendet, 0 = TX-FIFO voll (spaeter erneut), -1 = nicht verbunden oder nicht abonniert
 */
int app_att_send_events (u8 *p, int len);




#endif /* BLM_ATT_H_ */
