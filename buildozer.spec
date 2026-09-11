[app]
title = Table Buddy
package.name = tablebuddy
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,wav,mp3,ttf
version = 0.1
requirements = python3,pygame-ce
orientation = landscape
fullscreen = 1

[buildozer]
log_level = 2
warn_on_root = 1

[android]
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.permissions = INTERNET
android.archs = arm64-v8a
