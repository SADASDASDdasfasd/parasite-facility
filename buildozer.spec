[app]
title = PARASITE FACILITY
package.name = parasitefacility
package.domain = org.parasite

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0.0

requirements = python3,kivy==2.2.1,kivymd

orientation = landscape
fullscreen = 1

android.permissions = VIBRATE
android.api = 33
android.minapi = 26
android.ndk = 25b
android.sdk = 33
android.ndk_api = 26
android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True
android.wakelock = False

# Icon / presplash (add your own files if desired)
# icon.filename = %(source.dir)s/data/icon.png
# presplash.filename = %(source.dir)s/data/presplash.png
presplash.color = #000000

[buildozer]
log_level = 2
warn_on_root = 1
