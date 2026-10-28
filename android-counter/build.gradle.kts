plugins {
    id("com.android.application") version "9.4.0" apply false
    // muss zur Kotlin-Version passen, die AGP 9.4.0 mitbringt (2.2.10)
    id("org.jetbrains.kotlin.plugin.compose") version "2.2.10" apply false
}
