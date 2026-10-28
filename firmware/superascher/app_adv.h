/********************************************************************************************************
 * @file    app_adv.h
 *
 * @brief   Superascher: Advertising mit wechselndem Takt und Zählerstand in den Werbedaten
 *
 *          Ruhe: alle 1 s (Strom sparen, Handy findet den Ascher trotzdem für den Abgleich).
 *          Nach einem Stempeldruck: 30 s lang alle 100 ms, damit ein Handy mit Hintergrund-Scan
 *          sofort reagiert. Der Zählerstand steht als Manufacturer Data in jedem Werbepaket,
 *          das Handy erkennt neue Ereignisse also schon ohne Verbindung.
 *
 *******************************************************************************************************/
#ifndef APP_ADV_H_
#define APP_ADV_H_

#include "tl_common.h"

/**
 * @brief   Werbedaten setzen und im Ruhetakt starten (einmal beim Power-on).
 * @param   count - aktueller Zählerstand
 */
void app_adv_init(u32 count);

/**
 * @brief   Neues Ereignis: Zählerstand aktualisieren und für eine Weile schnell werben.
 * @param   count - neuer Zählerstand
 */
void app_adv_burst(u32 count);

/**
 * @brief   Nach Ablauf der Schnellphase zurück in den Ruhetakt (aus dem main_loop aufrufen).
 */
void app_adv_loop(void);

/**
 * @brief   Läuft gerade die Schnellphase?
 */
int app_adv_is_fast(void);

#endif /* APP_ADV_H_ */
