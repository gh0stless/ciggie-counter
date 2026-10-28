/********************************************************************************************************
 * @file    app_log.c
 *
 * @brief   Superascher: Ereignisprotokoll (Stempeldruecke mit Zeitstempel) im Flash und Geraeteuhr
 *
 *          Jedes Ereignis: u32 seq (fortlaufend, Bit 31 = Zeit unbekannt) + u32 time (Unix-Zeit).
 *          Die App stellt bei jeder Verbindung die Uhr und holt per "Events" alle Ereignisse ab
 *          der Nummer, die sie zuletzt erhalten hat. Das Geraet loescht nie auf Anforderung, der
 *          Ringpuffer ueberschreibt nur die aeltesten Eintraege (1024 Ereignisse).
 *
 *******************************************************************************************************/
#include "tl_common.h"
#include "drivers.h"
#include "stack/ble/ble.h"

#include "app_att.h"
#include "app_log.h"
#include "app_adv.h"


#define LOG_REC_NUM					(LOG_SECTOR_SIZE * LOG_SECTOR_NUM / LOG_REC_SIZE)
#define LOG_REC_PER_SECTOR			(LOG_SECTOR_SIZE / LOG_REC_SIZE)
#define LOG_SEQ_EMPTY				0xFFFFFFFF		//geloeschter Flash
#define LOG_SEQ_MASK				(~LOG_SEQ_TIME_UNKNOWN)
#define TICKS_PER_S					(1000000 * sys_tick_per_us)
#define SYNC_RECS_PER_NOTIFY		2				//2 x 8 Byte passen in ein Notify bei Standard-MTU (20 Byte)

/* Rueckmeldung "Abgleich fertig": blaue LED 3x kurz (an, aus, an, aus, an, aus) */
#define LED_SYNC_BLINKS				3
#define LED_SYNC_STEP_US			200000

typedef struct{
	u32 seq;
	u32 time;
}log_rec_t;

_attribute_ble_data_retention_	static u32 log_next_seq;		//Nummer des naechsten Ereignisses = Gesamtzahl
_attribute_ble_data_retention_	static u32 log_next_slot;		//naechster freier Platz im Ringpuffer
_attribute_ble_data_retention_	static u32 log_boot_first_seq;	//erstes Ereignis seit diesem Start
_attribute_ble_data_retention_	static u32 log_pending;			//vorgemerkte, noch nicht gespeicherte Stempel

_attribute_ble_data_retention_	static u32 uptime_s;			//Sekunden seit Start
_attribute_ble_data_retention_	static u32 uptime_tick;
_attribute_ble_data_retention_	static u32 unix_offset;			//Unix-Zeit = uptime_s + unix_offset, 0 = Uhr nicht gestellt
_attribute_ble_data_retention_	static u32 time_shown;

_attribute_ble_data_retention_	static u32 sync_seq;			//naechstes zu sendendes Ereignis
_attribute_ble_data_retention_	static u8  sync_active;

_attribute_ble_data_retention_	static u8  led_steps;			//verbleibende Wechsel an/aus
_attribute_ble_data_retention_	static u32 led_tick;


static void log_read(u32 slot, log_rec_t *rec)
{
	flash_read_page(LOG_FLASH_ADDR + slot * LOG_REC_SIZE, LOG_REC_SIZE, (u8 *)rec);
}

static u32 log_unix_time(void)
{
	return unix_offset ? uptime_s + unix_offset : 0;
}

static void log_update_uptime(void)
{
	u32 elapsed = (u32)(clock_time() - uptime_tick) / TICKS_PER_S;
	if(elapsed){
		uptime_s += elapsed;
		uptime_tick += elapsed * TICKS_PER_S;
	}
}


void app_log_init(void)
{
	log_rec_t rec;
	u32 found = 0;

	log_next_seq = 0;
	log_next_slot = 0;
	for(u32 slot = 0; slot < LOG_REC_NUM; slot++){
		log_read(slot, &rec);
		if(rec.seq == LOG_SEQ_EMPTY){
			continue;
		}
		u32 seq = rec.seq & LOG_SEQ_MASK;
		if(!found || seq >= log_next_seq){
			log_next_seq = seq + 1;
			log_next_slot = (slot + 1) % LOG_REC_NUM;
			found = 1;
		}
	}

	log_boot_first_seq = log_next_seq;
	log_pending = 0;
	uptime_s = 0;
	uptime_tick = clock_time();
	unix_offset = 0;
	time_shown = 0;
	sync_active = 0;
	led_steps = 0;

	app_att_set_count(log_next_seq);
	app_att_set_time(0);
	app_adv_init(log_next_seq);
	tlkapi_send_string_u32s(APP_LOG_EN, "[APP][LOG] init, Ereignisse", log_next_seq, log_next_slot);
}


void app_log_stamp(void)
{
	log_pending ++;
}


void app_log_set_time(u32 unix_time)
{
	log_update_uptime();
	unix_offset = unix_time - uptime_s;
	tlkapi_send_string_u32s(APP_LOG_EN, "[APP][LOG] Uhr gestellt", unix_time);
}


void app_log_request(u32 from_seq)
{
	if(log_next_seq - from_seq > LOG_REC_NUM && from_seq < log_next_seq){  //aelter als der Ringpuffer: ab dem aeltesten senden
		from_seq = log_next_seq - LOG_REC_NUM;
	}
	sync_seq = from_seq;
	sync_active = 1;
}


static void log_write_event(void)
{
	u32 slot = log_next_slot;
	if((slot % LOG_REC_PER_SECTOR) == 0){  //neuer Sektor: aelteste Ereignisse verwerfen
		flash_erase_sector(LOG_FLASH_ADDR + slot * LOG_REC_SIZE);
	}

	log_rec_t rec;
	if(unix_offset){
		rec.seq = log_next_seq;
		rec.time = log_unix_time();
	}
	else{
		rec.seq = log_next_seq | LOG_SEQ_TIME_UNKNOWN;
		rec.time = uptime_s;
	}
	flash_write_page(LOG_FLASH_ADDR + slot * LOG_REC_SIZE, LOG_REC_SIZE, (u8 *)&rec);

	log_next_seq ++;
	log_next_slot = (slot + 1) % LOG_REC_NUM;
	tlkapi_send_string_u32s(APP_LOG_EN, "[APP][LOG] Ereignis", rec.seq, rec.time);
}


/* Ereignis mit Nummer seq aus dem Ringpuffer holen, 0 wenn schon ueberschrieben */
static int log_find(u32 seq, log_rec_t *rec)
{
	u32 back = log_next_seq - seq;
	if(back == 0 || back > LOG_REC_NUM){
		return 0;
	}
	log_read((log_next_slot + LOG_REC_NUM - back) % LOG_REC_NUM, rec);
	if(rec->seq == LOG_SEQ_EMPTY || (rec->seq & LOG_SEQ_MASK) != seq){
		return 0;
	}

	/* Ereignis aus diesem Start, Uhr inzwischen gestellt: Zeit nachtraeglich umrechnen */
	if((rec->seq & LOG_SEQ_TIME_UNKNOWN) && seq >= log_boot_first_seq && unix_offset){
		rec->seq = seq;
		rec->time += unix_offset;
	}
	return 1;
}


static void log_led_start(void)
{
#if (UI_LED_ENABLE)
	led_steps = LED_SYNC_BLINKS * 2 - 1;
	led_tick = clock_time();
	gpio_write(GPIO_LED_BLUE, LED_ON_LEVAL);
#endif
}

static void log_led_loop(void)
{
#if (UI_LED_ENABLE)
	if(led_steps && clock_time_exceed(led_tick, LED_SYNC_STEP_US)){
		led_tick = clock_time();
		led_steps --;
		gpio_write(GPIO_LED_BLUE, (led_steps & 1) ? LED_ON_LEVAL : !LED_ON_LEVAL);
	}
#endif
}

int app_log_busy(void)
{
	return led_steps != 0;
}


static void log_sync_loop(void)
{
	while(sync_active){
		if(sync_seq >= log_next_seq){  //fertig: Endemarke mit Gesamtzahl
			int ret = app_att_send_events((u8 *)&log_next_seq, 4);
			if(ret != 0){  //gesendet oder niemand abonniert
				sync_active = 0;
			}
			if(ret > 0){
				log_led_start();
			}
			return;
		}

		log_rec_t recs[SYNC_RECS_PER_NOTIFY];
		u32 n = 0;
		u32 seq = sync_seq;
		while(n < SYNC_RECS_PER_NOTIFY && seq < log_next_seq){
			if(log_find(seq, &recs[n])){
				n ++;
			}
			seq ++;
		}

		if(n){
			int ret = app_att_send_events((u8 *)recs, n * LOG_REC_SIZE);
			if(ret == 0){	//TX-FIFO voll, im naechsten Durchlauf weiter
				return;
			}
			if(ret < 0){	//Verbindung weg oder nicht abonniert
				sync_active = 0;
				return;
			}
		}
		sync_seq = seq;
	}
}


void app_log_loop(void)
{
	log_update_uptime();

	while(log_pending){
		log_pending --;
		log_write_event();
		app_att_set_count(log_next_seq);
		app_adv_burst(log_next_seq);
	}

	u32 now = log_unix_time();
	if(now != time_shown){
		time_shown = now;
		app_att_set_time(now);
	}

	log_sync_loop();
	log_led_loop();
	app_adv_loop();
}
