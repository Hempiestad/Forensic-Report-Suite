import sys
p=r'd:\\Fortensic Suite Project\\Forensic-Report-and-Notes-main\\reports_tab.py'
s=open(p,'r',encoding='utf-8',errors='replace').read()
for q in ['"""',"'''"]:
    idx=s.find(q)
    if idx!=-1:
        line = s.count('\n',0,idx)+1
        print(q, 'first at line', line)
    else:
        print(q, 'not found')
# find all occurrences
for q in ['"""',"'''"]:
    i=0
    print('\nOccurrences of',q)
    while True:
        idx=s.find(q,i)
        if idx==-1:
            break
        line=s.count('\n',0,idx)+1
        snippet=s[max(0,idx-40):idx+60]
        print('line',line, 'context ->', snippet.replace('\n','\\n'))
        i=idx+len(q)
print('\n--- EOF tail ---\n')
print(s[-500:])
