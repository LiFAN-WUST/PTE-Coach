"""Independent hypothesis/reference edit alignment; never repairs the hypothesis."""
import re
from collections import Counter

PATTERN = re.compile(r"[a-z]+(?:'[a-z]+)?|\d+(?:\.\d+)?", re.I)

def tokens(text):
    return PATTERN.findall(text.lower().replace('’', "'"))

def compare(reference, hypothesis):
    a,b=tokens(reference),tokens(hypothesis)
    n,m=len(a),len(b)
    dp=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1): dp[i][0]=i
    for j in range(m+1): dp[0][j]=j
    for i in range(1,n+1):
        for j in range(1,m+1):
            dp[i][j]=min(dp[i-1][j]+1,dp[i][j-1]+1,dp[i-1][j-1]+(a[i-1]!=b[j-1]))
    ops=[]; i,j=n,m
    while i or j:
        if i and j and dp[i][j]==dp[i-1][j-1]+(a[i-1]!=b[j-1]):
            ops.append({'kind':'match' if a[i-1]==b[j-1] else 'substitution','reference':a[i-1],'spoken':b[j-1],'reference_index':i-1,'spoken_index':j-1}); i-=1;j-=1
        elif i and dp[i][j]==dp[i-1][j]+1:
            ops.append({'kind':'omission','reference':a[i-1],'spoken':None,'reference_index':i-1,'spoken_index':None});i-=1
        else:
            ops.append({'kind':'insertion','reference':None,'spoken':b[j-1],'reference_index':None,'spoken_index':j-1});j-=1
    ops.reverse()
    counts={k:0 for k in ['match','omission','insertion','substitution']}
    counts.update(Counter(x['kind'] for x in ops))
    # Flag repeated blocks only when at least one token is an insertion: avoids penalizing "had had" in the reference.
    inserted={x['spoken_index'] for x in ops if x['kind']=='insertion'}
    repetitions=[]; covered=set()
    for length in range(3,0,-1):
        for j in range(length,m-length+1):
            indexes=set(range(j,j+length))
            prior=set(range(j-length,j))
            if b[j-length:j]==b[j:j+length] and (indexes|prior)&inserted and not indexes&covered:
                repetitions.append({'start_index':j,'length':length,'text':' '.join(b[j:j+length]),'status':'ASR-observed candidate'})
                covered|=indexes
    return {'reference_tokens':a,'spoken_tokens':b,'operations':ops,'counts':counts,'wer':dp[n][m]/max(1,n),
            'repetitions':repetitions,'fillers':[{'index':i,'text':w} for i,w in enumerate(b) if w in {'um','uh','erm','hmm'}],
            'word_order':'represented by edit operations; no semantic reorder diagnosis',
            'restarts':None,'self_corrections':None}
