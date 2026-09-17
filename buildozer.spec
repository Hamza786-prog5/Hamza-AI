[app]
title = Hamza AI
package.name = hamzaai
package.domain = com.hamza
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 1.0
requirements = python3,kivy
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.arch = arm64-v8a