
# coding: utf-8

# In[1]:


import math, re
from pprint import pprint
from collections import Counter, defaultdict

count = dict()
count_c = defaultdict(lambda: 0)
for line in open('count_1edit.txt', 'r', encoding='utf8'):
    wc, num = line.strip().split('\t')
    w, c = wc.split('|')
    count[(w, c)] = int(num)
    count_c[c] += int(num)
Ncount = Counter(count.values())

Nall = len(count.keys())
N0 = 26*26*26*26+2*26*26*26+26*26 - Nall
Nr = [ N0 if r == 0 else Ncount[r] for r in range(12) ]

def smooth(count, r=10):
    if count <= r:
        return (count+1)*Nr[count+1] / Nr[count]
    else:
        return count

def Pedit(w, c):
    if (w, c) not in count and count_c[c] > 0:
        return smooth(0) / count_c[c]
    if count_c[c] > 0:
        return smooth(count[(w, c)]) / count_c[c]
    else:
        return 0

def words(text): return re.findall(r'\w+', text.lower())

WORDS = Counter(words(open('big.txt').read()))
# WORDS = Counter(open('big.txt').read().split())

def Pw(word, N=sum(WORDS.values())): 
    "Probability of `word`."
    return WORDS[word] / N

def correction(word): 
    "Most probable spelling correction for word."
    states = [ ('', word, 0, Pw(word), 1) ]
    for i in range(len(word)):
        # print(i, states[:3])
        STATES = [ s for state in states for s in next_states(state) ]
        states = sorted(STATES, key=lambda x: x[2])

        unique, new_states = set(), []
        for state in states:
            if state[0] + state[1] in unique: continue

            unique.add(state[0] + state[1])
            new_states.append(state)
        states = new_states
        states = sorted(states, key=lambda x: P(x[3], x[4]), reverse=True) [:500]# [:MAXBEAM]
    return states[:10]

def next_states(state):
    letters    = 'abcdefghijklmnopqrstuvwxyz'
    L, R, edit, prob, ped = state
    R0, R1 = R[0], R[1:]
    if edit == 2: return [( L + R0, R1, edit, prob, ped*0.8 )]
    noedit    = [( L + R0, R1, edit, prob, ped*0.8 )]
    delete    = [( L, R1, edit+1, Pw(L + R1), ped * Pedit(L[-1]+R0, L[-1]))]  if len(L) > 0 else []
    insert    = [( L + R0 + c, R1, edit+1, Pw(L + R0 + c + R1), ped * Pedit(R0, R0 + c) ) for c in letters]
    replace   = [( L + c, R1, edit+1, Pw(L + c + R1), ped * Pedit(R0, c) ) for c in letters]
    transpose = [( L[:-1] + R0 + L[-1], R1, edit+1, Pw(L[:-1] + R0 + L[-1] + R1), ped * Pedit(L[-1]+R0, R0+L[-1]) )] if len(L) > 1 else []
    return set(noedit + delete + replace + insert + transpose)

'''Combining channel probability with word probability to score states'''
def P(pw, pedit):
    return pw*pedit


# In[2]:


import requests

API_URL = "http://api.netspeak.org/netspeak3/search?query=%s"

class NetSpeak:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (compatible; MSIE 5.5; Windows NT)'}
        self.page = None
        self.dictionary = {}

    def __getPageContent(self, url):
        return requests.get(url, headers=self.headers).text
        # return self.opener.open(url).read()

    def __rolling(self, url, maxfreq=None):
        if maxfreq:
            webdata = self.__getPageContent(url + "&maxfreq=%s" % maxfreq)
        else:
            webdata = self.__getPageContent(url)
        if webdata:
            # webdata = webdata.decode('utf-8')
            results = [data.split('\t') for data in webdata.splitlines()]
            results = [(data[2], float(data[1])) for data in results]
            lastFreq = int(results[-1][1])
            if lastFreq != maxfreq:
                return results + self.__rolling(url, lastFreq)
            else:
                return []
        else:
            return []

    def search(self, query):
        if query in self.dictionary: return self.dictionary[query]
        
        queries = query.lower().split()
        new_query = []
        for token in queries:
            if token.count('|') > 0:
                new_query.append('[+{0}+]'.format('+'.join(token.split('|'))))
            elif token == '*':
                new_query.append('?')
            else:
                new_query.append(token)
        new_query = '+'.join(new_query)
        url = API_URL % (new_query.replace(' ', '+'))
        self.dictionary[query] = self.__rolling(url)
        return self.dictionary[query]
    
SE = NetSpeak() # singleton


# In[3]:


confuse_word = open('lab4.confusables.txt','r').readlines()
Confuse = {}
for line in confuse_word:
    w ,c = line.split('\t')
    Confuse[w]=c.strip()


# In[4]:


def get_trigrams(tokens):
    return [tokens[i:i+3] for i in range(len(tokens) - 2)]


# In[5]:


def detect_where(tm):
    trigrams = get_trigrams(tm)
    tri_tmp = []
    for index,tri in enumerate(trigrams):
        #print(tri)
        res = SE.search(' '.join(tri))
        #print(res)
        if res:
            tri_tmp.append((index,res[0][1],tri))
        else:
            tri_tmp.append((index,0,tri))
    #print(tri_tmp)
    minn  = min(tri_tmp,key=lambda x:x[1])[2]
    #print(minn)
    for find_index in tri_tmp:
        #print(find_index[2])
        if find_index[2]==minn:
            detect_sentence = find_index
            
    return detect_sentence

def find_the_best(tm,start):
    
    best = (None, None, None, None, -math.inf)
    #find_the_best = []
    for i in range(start,start+3):
        candidate = []
        for corr in correction(tm[i]):
            candidate.append(corr[0])
        if tm[i] in Confuse.keys():
            candidate.append(tm[i])
        #print(candidate)
        for cancan in candidate:
            count = 1.0
            combine = tm[:i] + [cancan] + tm[i+1:]
            #print(combine)
            trigrams = get_trigrams(combine)
            
            for tri in trigrams:
                res = SE.search(' '.join(tri))
                count *= res[0][1] if res else 0
                #print(res,count)
                
            best = (combine,tm[i],cancan,candidate,count) if count > best[-1] else best
       
    return best


# In[6]:


#分割正確跟錯誤的資料集
line = open('lab4.test.1.txt','r').readlines()
Correct_sentence = []
False_sentence = []
for sentence in line:
    tmp = sentence.split('\t')
    False_sentence.append(tmp[0].strip().lower())
    Correct_sentence.append(tmp[1].strip().lower())
test_Correct=Correct_sentence[:20]
test_False = False_sentence[:20]


# In[7]:


hits = 0
arm = 0
for i,line in enumerate (test_False):
    word = line.split(' ')
    detect_sentence = detect_where(word)
    start = detect_sentence[0]
    combine ,wrong ,right ,candidate ,_ =find_the_best(word,start)
    combine = ' '.join(combine).strip()
    if combine == test_Correct[i]:
        hits+=1
    arm += 1
    
    f = open('lab4_106065503.txt','a')
    
    print("Error:" +  str(wrong))
    f.write("Error:" +  str(wrong)+'\n')
    
    print("Candidates:", candidate)
    f.write("Candidates:" +  str(candidate)+'\n')
    
    print("Correction:", right)
    f.write("Correction:" +  str(right)+'\n')
    
    print(test_False[i], "->", combine )
    f.write(test_False[i] + "->" + combine+'\n')
    
    print("hits =", hits)
    f.write("hits ="+ str(hits)+'\n\n')
    
    print()
    
f = open('lab4_106065503.txt','a')

print("Precision:", hits/arm)
f.write("Precision:"+ str(hits/arm)+'\n')

print("FalseAlarm:", (arm-hits)/arm)
f.write("FalseAlarm:"+str((arm-hits)/arm)+'\n')

f.close()
    

