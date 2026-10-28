/********************************************************************************************************
 * @file    app_log.h
 *
 * @brief   Superascher: Ereignisprotokoll (Stempeldruecke mit Zeitstempel) im Flash und Geraeteuhr
 *
 *******************************************************************************************************/
#ifndef APP_LOG_H_
#define APP_LOG_H_

#include "tl_common.h"

/* Ringpuffer im Flash: 2 Sektoren ab 0x70000, frei laut vendor/common/ble_flash.h
 * (Firmware 0x00000, OTA 0x20000, MAC 0x76000, Kalibrierung 0x77000, SMP 0x78000) */
#define LOG_FLASH_ADDR					0x70000
#define LOG_SECTOR_SIZE					4096
#define LOG_SECTOR_NUM					2
#define LOG_REC_SIZE					8

/* Bit 31 der Ereignisnummer: Zeit ist "Sekunden seit Start" statt Unix-Zeit (Uhr war nicht gestellt) */
#define LOG_SEQ_TIME_UNKNOWN			BIT(31)


/**
 * @brief   Ringpuffer durchsuchen und Zaehlerstand wiederherstellen (nach Power-on).
 */
void app_log_init(void);

/**
 * @brief   Uhr fortschreiben, vorgemerkte Stempel speichern, laufenden Abgleich senden.
 *          Muss mindestens alle 268 s laufen (Ueberlauf System-Timer), im main_loop gegeben.
 */
void app_log_loop(void);

/**
 * @brief   Stempeldruck vormerken. Gespeichert wird in app_log_loop (nicht im Tasten-Callback).
 */
void app_log_stamp(void);

/**
 * @brief   Uhr stellen (von der App bei jeder Verbindung).
 * @param   unix_time - Sekunden seit 1970 (UTC)
 */
void app_log_set_time(u32 unix_time);

/**
 * @brief   Abgleich starten: alle Ereignisse ab dieser Nummer per Notify senden.
 * @param   from_seq - erste gewuenschte Ereignisnummer
 */
void app_log_request(u32 from_seq);

/**
 * @brief   Laeuft gerade eine LED-Rueckmeldung? Dann darf nicht geschlafen werden.
 * @return  1 = beschaeftigt
 */
int app_log_busy(void);

#endif /* APP_LOG_H_ */
