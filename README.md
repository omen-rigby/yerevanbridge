# yerevanbridge
Yerevan bridge club site

# Localization instructions for developers
Project uses pybabel: https://python-babel.github.io/flask-babel/index.html
Here's the cheat sheet of commands to use:
pybabel extract -F babel.cfg -o messages.pot .
pybabel update -i messages.pot -d translations
pybabel compile -d translations
