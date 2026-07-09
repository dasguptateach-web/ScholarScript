import frontmatter, markdown

path = r'C:\Users\81\ScholarScript\content\papers\french-influence-on-the-english-language.md'
with open(path, 'r', encoding='utf-8') as f:
    post = frontmatter.load(f)

print('Title:', post.metadata.get('title'))
print('Date:', post.metadata.get('date'))
print('Type:', post.metadata.get('type'))

body = post.content

html = markdown.markdown(body, extensions=['extra', 'codehilite', 'toc', 'sane_lists'])
print('HTML length:', len(html))

if '<table>' in html:
    print('Tables found:', html.count('<table>'))
else:
    print('Tables NOT found - checking why...')
    if 'Period' in html:
        idx = html.find('Period')
        print('Table content found at', idx, ':')
        print(html[idx:idx+500])
    else:
        print('No table content in HTML')
        print('Last 500 of body:')
        print(body[-500:])
