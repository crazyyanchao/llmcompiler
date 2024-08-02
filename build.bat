
del /f /q dist\*.*
python setup.py sdist
twine upload -r nexus dist\*
