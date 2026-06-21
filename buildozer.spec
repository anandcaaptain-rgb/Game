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

android.permissions = INTERNET

# Modern Android settings
android.api = 33
android.minapi = 21

[buildozer]

log_level = 2
warn_on_root = 1
