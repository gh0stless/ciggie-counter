package de.superascher.counter

import android.app.Application
import de.superascher.counter.ashtray.Background
import de.superascher.counter.reminder.Reminders

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        Reminders.createChannel(this)
        Reminders.reschedule(this)
        Background.schedule(this)
    }
}
