[app]

title = Flappy Bird
package.name = flappybird
package.domain = org.anand

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,wav,mp3

version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 21
android.ndk = 25b

android.permissions = INTERNET

# Uncomment if you add an icon
# icon.filename = icon.png

[buildozer]

log_level = 2
warn_on_root = 1
