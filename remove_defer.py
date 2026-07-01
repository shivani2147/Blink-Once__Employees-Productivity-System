import os, glob

for file in glob.glob('public/*.html'):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove defer from theme.js
    new_content = content.replace('<script src="/static/js/theme.js" defer></script>', '<script src="/static/js/theme.js"></script>')
    
    if new_content != content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated {file}')
