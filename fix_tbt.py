path = 'frontend/app.html'
content = open(path, encoding='utf-8').read()

# Push GTM load delay from 3s to 5s to get outside TBT window
old = 'setTimeout(loadGTM, 3000)'
new = 'setTimeout(loadGTM, 5000)'

if content.count(old) == 2:
    content = content.replace(old, new)
    open(path, 'w', encoding='utf-8').write(content)
    print('SUCCESS: GTM delay pushed to 5s (both occurrences)')
else:
    print(f'Found {content.count(old)} occurrences - expected 2')
